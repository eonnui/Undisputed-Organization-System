from sqlalchemy.orm import Session
from . import crud, models
import random
import os
from dotenv import load_dotenv
import ollama
import logging

load_dotenv()

logger = logging.getLogger(__name__)

class Chatbot:
    def __init__(self, db: Session, user_id: int = None, initial_history: list = None, current_page_path: str = None, page_content: str = None):
        self.db = db
        self.user_id = user_id
        self.model_name = "llama3" # Or "phi3" or another model you've downloaded with Ollama
        self.conversation_history = initial_history if initial_history is not None else []
        self.page_content = page_content # Store the current page content
        self.current_page_path = current_page_path # Store the current page path
        # Add a system message to inform the LLM about the page_content format and general conversational tone
        if not any(msg.get('role') == 'system' and 'You are a helpful and conversational assistant.' in msg.get('content', '') for msg in self.conversation_history):
            self.conversation_history.insert(0, {'role': 'system', 'content': 'You are a highly intelligent, accurate, and conversational assistant. Provide concise and precise answers. When asked about the current page, analyze the provided HTML content deeply to give smart, context-aware, and specific explanations. For general questions, respond as a knowledgeable AI.'})


    def _send_message_to_ollama(self, message: str):
        self.conversation_history.append({'role': 'user', 'content': message})
        logger.info(f"Sending message to Ollama: {message}")
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
        message_lower = message.lower()

        if "upcoming event" in message_lower or "next event" in message_lower:
            return self._get_upcoming_events_response()
        elif "event details" in message_lower or "info about event" in message_lower:
            # LLM will extract event name, then we retrieve details
            event_title = self._extract_entity_with_llm(message, "event title")
            if event_title:
                return self._get_event_details_response(event_title)
            return "Please specify the name of the event you'd like to know more about."
        elif "membership fee" in message_lower or "semester fee" in message_lower:
            return self._get_membership_fee_response()
        elif "contact information" in message_lower or "who to contact" in message_lower:
            return self._get_contact_information_response()
        elif "payment history" in message_lower:
            return self._get_payment_history_response()
        elif "bulletin post details" in message_lower or "info about bulletin" in message_lower:
            # LLM will extract post title, then we retrieve details
            post_title = self._extract_entity_with_llm(message, "bulletin post title")
            if post_title:
                return self._get_bulletin_post_details_response(post_title)
            return "Please specify the title of the bulletin board post you'd like to know more about."
        elif "bulletin board" in message_lower or "bulletin post" in message_lower:
            return self._get_bulletin_posts_response()
        elif "rule details" in message_lower or "policy details" in message_lower:
            # LLM will extract rule title, then we retrieve details
            rule_title = self._extract_entity_with_llm(message, "rule or policy title")
            if rule_title:
                return self._get_rule_wiki_entry_details_response(rule_title)
            return "Please specify the title of the rule or policy you'd like to know more about."
        elif "rules in category" in message_lower or "policy in category" in message_lower:
            # LLM will extract category, then we retrieve rules
            category = self._extract_entity_with_llm(message, "category of rules")
            if category:
                return self._get_rule_wiki_entries_by_category_response(category)
            return "Please specify the category of rules you'd like to know more about."
        elif "rule" in message_lower or "policy" in message_lower or "handbook" in message_lower:
            return self._get_rule_wiki_entries_response()
        elif "what can you do" in message_lower or "capabilities" in message_lower:
            return self._get_chatbot_capabilities_response()
        elif "where am i" in message_lower or "what is this page" in message_lower or "what do i do here" in message_lower or "guide me" in message_lower:
            return self._get_page_guidance_response()
        elif "what is" in message_lower or "explain" in message_lower or "tell me about" in message_lower:
            element_name = self._extract_entity_with_llm(message, "page element")
            if element_name:
                return self._explain_page_element(element_name)
            return "Please specify which element you'd like me to explain."
        elif "explain the data" in message_lower or "what does this say" in message_lower or "interpret this" in message_lower or "what is that" in message_lower:
            return self._explain_current_page_data(message)
        elif "thank you" in message_lower or "thanks" in message_lower:
            return self._get_thank_you_response()
        elif "hello" in message_lower or "hi" in message_lower or "hey" in message_lower:
            return self._get_greeting_response()
        elif "bye" in message_lower or "goodbye" in message_lower or "farewell" in message_lower:
            return self._get_farewell_response()
        
        return None

    def _get_page_guidance_response(self) -> str:
        if not self.current_page_path:
            return "I'm not sure which page you are on. Please try navigating to a specific page first."

        prompt = f"The user is currently on the page with the URL path: {self.current_page_path}. Here is the full HTML content of the page:\n\n{self.page_content}\n\nIn one concise sentence, what is the main purpose of this page and what can a user typically do here?"
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

        data_output = ""
        if data_type == "payments":
            payments = crud.get_user_payments(self.db, self.user_id)
            if payments:
                data_output += "User Payment History:\n"
                for payment in payments:
                    status = "Paid" if payment.status == "completed" else "Pending"
                    data_output += f"- Amount: ₱{payment.amount:.2f}, Status: {status}, Date: {payment.created_at.strftime('%Y-%m-%d')}\n"
            else:
                data_output += "No payment history found for this user.\n"
        elif data_type == "events":
            # Assuming a crud function like get_user_registered_events or similar
            # For now, let's just get all events and let LLM filter if needed
            events = crud.get_all_events(self.db) 
            if events:
                data_output += "All Events (user's organization):\n"
                for event in events:
                    data_output += f"- {event.title} on {event.date.strftime('%Y-%m-%d')}, Location: {event.location}\n"
            else:
                data_output += "No events found.\n"
        # Add more data types as needed (e.g., "profile", "bulletin_posts_liked")
        
        return data_output

    def _explain_current_page_data(self, user_query: str) -> str:
        if not self.page_content:
            return "I don't have the content of this page to explain. Please ensure the page content is being sent."

        # Determine if the query is asking for user-specific data
        user_data_context = ""
        query_lower = user_query.lower()
        if "my payment" in query_lower or "my fee" in query_lower or "my balance" in query_lower or "2000 pesos" in query_lower or "amount" in query_lower:
            user_data_context = self._get_user_specific_data("payments")
        elif "my event" in query_lower or "my schedule" in query_lower:
            user_data_context = self._get_user_specific_data("events")
        # Add more conditions for other user-specific data types

        prompt = f"The user's specific question is: '{user_query}'.\n\n"                 f"Please analyze the following full HTML page content and any provided user-specific data. Then, in a very brief, accurate, and conversational way, explain the context and meaning of the data point mentioned in the user's question. If the question is about a number, explain what that number is for. If it's about an image, explain what the image is for. Be extremely specific and to the point.\n\n"                 f"Full HTML Page Content:\n{self.page_content}\n\n"                 f"User-Specific Data (if relevant):\n{user_data_context}"
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

    
