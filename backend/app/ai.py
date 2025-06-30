from sqlalchemy.orm import Session
from . import crud, models
import random
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

class Chatbot:
    def __init__(self, db: Session, user_id: int = None):
        self.db = db
        self.user_id = user_id
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def get_response(self, message: str) -> str:
        # First, try to handle specific queries using existing functions (RAG approach)
        response = self._handle_specific_queries(message)
        if response:
            return response
        
        # If no specific query matched, use the LLM for general conversation
        try:
            chat_session = self.model.start_chat(history=[])
            llm_response = chat_session.send_message(message)
            return llm_response.text
        except Exception as e:
            print(f"Error communicating with Gemini API: {e}")
            return "I'm sorry, I'm having trouble connecting to my knowledge base right now. Please try again later."

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
        elif "thank you" in message_lower or "thanks" in message_lower:
            return self._get_thank_you_response()
        elif "hello" in message_lower or "hi" in message_lower or "hey" in message_lower:
            return self._get_greeting_response()
        elif "bye" in message_lower or "goodbye" in message_lower or "farewell" in message_lower:
            return self._get_farewell_response()
        
        return None

    def _extract_entity_with_llm(self, message: str, entity_type: str) -> str | None:
        prompt = f"From the following message, extract the {entity_type}: '{message}'. If no {entity_type} is clearly specified, respond with 'None'."
        try:
            response = self.model.generate_content(prompt)
            extracted_text = response.text.strip()
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

    
