from sqlalchemy.orm import Session
from . import crud, models
import random
import os
from dotenv import load_dotenv
import ollama
import logging
import json
from bs4 import BeautifulSoup

load_dotenv()

logger = logging.getLogger(__name__)

class Chatbot:
    def __init__(self, db: Session, user_id: int = None, initial_history: list = None, current_page_path: str = None, page_content: str = None, page_data: dict = None):
        self.db = db
        self.user_id = user_id
        self.model_name = "llama3" # Or "phi3" or another model you've downloaded with Ollama
        self.conversation_history = initial_history if initial_history is not None else []
        self.page_content = page_content # Store the current page content
        self.current_page_path = current_page_path # Store the current page path
        self.page_data = page_data # Store the current page data (JSON)
        # Add a system message to inform the LLM about the page_content format and general conversational tone
        if not any(msg.get('role') == 'system' and 'You are a helpful, accurate, and reliable student assistant.' in msg.get('content', '') for msg in self.conversation_history):
            self.conversation_history.insert(0, {'role': 'system', 'content': '''You are a friendly and super helpful student assistant! My job is to give you clear, easy-to-understand answers about what you see and can do on this website. I'll always use simple words, no techy stuff! If you ask about something on the page, I'll talk about it like it's right there in front of you (like 'the big button' or 'the list of events'). My main goal is to help you quickly find what you need. If I'm not sure, I'll ask a quick question to get it right. Let's make things simple!'''})


    def _send_message_to_ollama(self, message: str):
        context_message = ""
        if self.current_page_path and self.page_content:
            context_message += f"Current page HTML content:\n\n{self.page_content}\n\n"
        if self.page_data:
            context_message += f"Additional page data: {json.dumps(self.page_data, indent=2)}\n\n"

        if context_message:
            full_message = f"{context_message}User's question: {message}"
        else:
            full_message = message
        self.conversation_history.append({'role': 'user', 'content': full_message})
        logger.info(f"Sending message to Ollama: {full_message}")
        response = ollama.chat(model=self.model_name, messages=self.conversation_history)
        llm_response = response['message']['content']
        logger.info(f"Received response from Ollama: {llm_response}")
        self.conversation_history.append({'role': 'assistant', 'content': llm_response})
        return llm_response

    def clear_conversation_history(self):
        self.conversation_history = []

    def _generate_content_with_ollama(self, prompt: str):
        logger.info(f"Generating content with Ollama, prompt: {prompt[:100]}...") # Log first 100 chars of prompt
        response = ollama.generate(model=self.model_name, prompt=prompt)
        llm_response = response['response']
        logger.info(f"Generated content from Ollama: {llm_response[:100]}...") # Log first 100 chars of response
        return llm_response

    def get_response(self, message: str) -> str:
        # First, try to handle specific queries using existing functions (RAG approach)
        response = self._handle_specific_queries(message)
        if response:
            logger.info(f"Returning specific query response: {response}")
            return response
        
        # If no specific query matched, use the LLM for general conversation
        try:
            llm_response = self._send_message_to_ollama(message)
            logger.info(f"Returning LLM response: {llm_response}")
            return llm_response
        except Exception as e:
            print(f"Error communicating with Ollama: {e}")
            return "I'm sorry, I'm having trouble connecting to my knowledge base right now. Please ensure Ollama is running and the model is available."

    def _handle_specific_queries(self, message: str) -> str | None:
        return None

    def _get_page_guidance_response(self) -> str:
        if not self.current_page_path:
            return "I'm not sure which page you are on. Please try navigating to a specific page first."

        prompt = f"Based on the following HTML content of the page:\n\n{self.page_content}\n\nIn one concise sentence, what is the main purpose of this page and what can a user typically do here?"
        try:
            response = self._generate_content_with_ollama(prompt)
            return response.strip()
        except Exception as e:
            print(f"Error generating page guidance with Ollama: {e}")
            return "I'm sorry, I'm having trouble generating guidance for this page right now."

    def _explain_page_element(self, element_name: str) -> str:
        if not self.current_page_path:
            return "I'm not sure which page you are on, so I can't explain elements on it."

        prompt = f"The user is currently on the page with the URL path: {self.current_page_path}. Here is the full HTML content of the page:\n\n{self.page_content}\n\nWhat is the '{element_name}' on this page for? Be extremely concise and accurate."
        try:
            response = self._generate_content_with_ollama(prompt)
            return response.strip()
        except Exception as e:
            print(f"Error explaining page element with Ollama: {e}")
            return f"I'm sorry, I'm having trouble explaining '{element_name}' right now."

    def _get_user_specific_data(self, data_type: str) -> str:
        if not self.user_id:
            return "I cannot retrieve user-specific data without a user ID."

        data_output = {}
        if data_type == "payments":
            payments = crud.get_user_payments(self.db, self.user_id)
            payment_history = []
            for payment in payments:
                if payment.payment_item: # Only include payments that have a linked PaymentItem
                    payment_item_status = "Paid" if payment.payment_item.is_paid else "Unpaid"
                    due_date = None
                    if payment.payment_item.due_date:
                        due_date = payment.payment_item.due_date.strftime('%Y-%m-%d')
                    
                    payment_history.append({
                        "amount": payment.amount,
                        "status": payment_item_status,
                        "date": payment.created_at.strftime('%Y-%m-%d'),
                        "due_date": due_date
                    })
            data_output["payments"] = payment_history
        elif data_type == "events":
            events = crud.get_all_events(self.db) 
            event_list = []
            for event in events:
                event_list.append({
                    "title": event.title,
                    "date": event.date.strftime('%Y-%m-%d'),
                    "location": event.location
                })
            data_output["events"] = event_list
        # Add more data types as needed (e.g., "profile", "bulletin_posts_liked")
        
        return data_output

    def _explain_current_page_data(self, user_query: str) -> str:
        if not self.page_content:
            return "I don't have the content of this page to explain. Please ensure the page content is being sent."

        # Determine if the query is asking for user-specific data
        user_data_context = {}
        query_lower = user_query.lower()
        
        # Existing user-specific data retrieval
        if "my payment" in query_lower or "my fee" in query_lower or "my balance" in query_lower or "2000 pesos" in query_lower or "amount" in query_lower:
            user_data_context["payments"] = self._get_user_specific_data("payments")["payments"]
        elif "my event" in query_lower or "my schedule" in query_lower:
            user_data_context["events"] = self._get_user_specific_data("events")["events"]
        
        # Comprehensive HTML parsing and data extraction for payment history
        if self.page_content and "/Payments/History" in self.current_page_path:
            soup = BeautifulSoup(self.page_content, 'html.parser')
            payment_records = []
            payment_status_counts = {}

            table_body = soup.find('table', class_='payment-history-table')
            if table_body:
                rows = table_body.find('tbody').find_all('tr')
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 7: # Ensure all expected columns are present
                        academic_year = cols[0].get_text(strip=True)
                        semester = cols[1].get_text(strip=True)
                        fee = cols[2].get_text(strip=True)
                        transaction = cols[3].get_text(strip=True)
                        status_span = cols[4].find('span', class_='status')
                        status = status_span.get_text(strip=True).lower() if status_span else "unknown"
                        due_date = cols[5].get_text(strip=True)
                        payment_date = cols[6].get_text(strip=True)

                        payment_records.append({
                            "academic_year": academic_year,
                            "semester": semester,
                            "fee": fee,
                            "transaction": transaction,
                            "status": status,
                            "due_date": due_date,
                            "payment_date": payment_date
                        })
                        payment_status_counts[status] = payment_status_counts.get(status, 0) + 1
            
            if payment_records:
                user_data_context['payment_history_data'] = payment_records
                logger.debug(f"Extracted payment history data from HTML: {payment_records}")
            if payment_status_counts:
                user_data_context['payment_status_counts'] = payment_status_counts
                logger.debug(f"Counted payment statuses from HTML: {payment_status_counts}")

        # Add more conditions for other user-specific data types and their HTML parsing
        # Example: if "/Events" in self.current_page_path: parse event details from HTML

        logger.debug(f"User data context for Ollama: {json.dumps(user_data_context, indent=2)}")

        prompt = f"""The user's question is: '{user_query}'.

Here is the relevant data:
{json.dumps(user_data_context, indent=2)}

Based *only* on the provided data, answer the user's question concisely and directly. If the question is about counts (e.g., how many paid items), use the numbers from "payment_status_counts" in the data. Do not add extra information or conversational filler. Just provide the answer.
"""
        try:
            response = self._generate_content_with_ollama(prompt)
            return response.strip()
        except Exception as e:
            print(f"Error explaining current page data with Ollama: {e}")
            return "I'm sorry, I'm having trouble explaining the data on this page right now."
        

    def _extract_entity_with_llm(self, message: str, entity_type: str) -> str | None:
        context = ""
        if entity_type == "page element" and self.current_page_path:
            context = f"The user is currently on the page: {self.current_page_path}. "

        prompt = f"{context}From the following message, extract the most relevant {entity_type} that the user is asking about. Be very specific. If no clear {entity_type} is mentioned, respond with 'None'. Message: '{message}'"
        try:
            response = self._generate_content_with_ollama(prompt)
            extracted_text = response.strip()
            if extracted_text.lower() == 'none':
                return None
            return extracted_text
        except Exception as e:
            print(f"Error extracting entity with LLM: {e}")
            return None

    def _get_greeting_response(self) -> str:
        return "Hello! How can I assist you today?"

    def _get_farewell_response(self) -> str:
        return "Goodbye! Have a great day!"

    

    def _get_upcoming_events_response(self) -> str:
        events = crud.get_all_events(self.db) # Assuming get_all_events exists in crud.py
        if not events:
            return "There are no upcoming events at the moment."

        response = "Here are the upcoming events:\n"
        for event in events:
            response += f"- {event.title} on {event.date.strftime('%Y-%m-%d')}\n"
        return response

    def _get_event_details_response(self, event_title: str) -> str:
        event = crud.get_event_by_title(self.db, event_title)
        if not event:
            return f"I couldn't find any event matching '{event_title}'. Please try a different name."

        return f"Details for {event.title}:\nDescription: {event.description}\nDate: {event.date.strftime('%Y-%m-%d %H:%M')}\nLocation: {event.location}\nMax Participants: {event.max_participants}\nParticipants Joined: {event.joined_count()}"

    def _get_membership_fee_response(self) -> str:
        # This information could be stored in the database in the future.
        return "The membership fee is ₱100 per semester."

    def _get_contact_information_response(self) -> str:
        president = crud.get_admin_by_position(self.db, "President")
        if president:
            return f"You can contact the organization president, {president.first_name} {president.last_name}, at {president.email}."
        return "I'm sorry, I don't have the contact information for the organization president at the moment."

    def _get_payment_history_response(self) -> str:
        # In a real application, you would get the user_id from the current session
        # For now, we'll use a placeholder or indicate that user context is needed.
        # Assuming a user_id of 1 for demonstration purposes.
        user_id = self.user_id
        payments = crud.get_user_payments(self.db, user_id)
        if not payments:
            return "You have no payment history recorded."

        response = "Here is your payment history:\n"
        for payment in payments:
            status = "Paid" if payment.status == "completed" else "Pending"
            response += f"- Amount: ₱{payment.amount:.2f}, Status: {status}, Date: {payment.created_at.strftime('%Y-%m-%d')}\n"
        return response

    def _get_bulletin_posts_response(self) -> str:
        posts = crud.get_all_bulletin_posts(self.db)
        if not posts:
            return "There are no bulletin board posts at the moment."

        response = "Here are the latest bulletin board posts:\n"
        for post in posts:
            response += f"- {post.title} (Category: {post.category}) - {post.created_at.strftime('%Y-%m-%d')}\n"
        return response

    def _get_bulletin_post_details_response(self, post_title: str) -> str:
        post = crud.get_bulletin_post_by_title(self.db, post_title)
        if not post:
            return f"I couldn't find any bulletin board post matching '{post_title}'. Please try a different title."

        return f"Details for {post.title}:\nContent: {post.content}\nCategory: {post.category}\nPosted On: {post.created_at.strftime('%Y-%m-%d')}"

    def _get_rule_wiki_entries_response(self) -> str:
        rules = crud.get_all_rule_wiki_entries(self.db)
        if not rules:
            return "There are no rule wiki entries at the moment."

        response = "Here are the rule wiki entries:\n"
        for rule in rules:
            response += f"- {rule.title} (Category: {rule.category})\n"
        return response

    def _get_rule_wiki_entry_details_response(self, rule_title: str) -> str:
        rule = crud.get_rule_wiki_entry_by_title(self.db, rule_title)
        if not rule:
            return f"I couldn't find any rule or policy matching '{rule_title}'. Please try a different title."

        return f"Details for {rule.title}:\nContent: {rule.content}\nCategory: {rule.category}"

    def _get_rule_wiki_entries_by_category_response(self, category: str) -> str:
        rules = crud.get_rule_wiki_entries_by_category(self.db, category)
        if not rules:
            return f"I couldn't find any rules in the category '{category}'. Please try a different category."

        response = f"Here are the rules in the '{category}' category:\n"
        for rule in rules:
            response += f"- {rule.title}\n"
        return response

    def _get_chatbot_capabilities_response(self) -> str:
        return """I can provide information on:\n- Upcoming events and event details\n- Membership fees\n- Contact information for the organization president\n- Your payment history\n- Bulletin board posts and their details\n- Rules and policies, including details and categories.\nJust ask me a question!"""

    def _get_thank_you_response(self) -> str:
        responses = [
            "You're welcome! Is there anything else I can help you with?",
            "No problem! Glad I could assist.",
            "Happy to help!",
            "Anytime!"
        ]
        import random
        return random.choice(responses)

    
