import json
from app.services.groq_service import ask_groq

async def detect_category_for_transaction(raw_data: str) -> str:
    """
    Detect transaction category using Groq AI based on raw transaction data.

    Args:
        raw_data: Raw transaction data as a JSON string.

    Returns:
        Predicted category as a string.
    """
    system_prompt = """You are a financial transaction categorizer.
Analyze the given raw transaction data and assign it to ONE of these categories:
- Food & Dining
- Transportation
- Shopping
- Entertainment
- Utilities
- Rent
- Education
- Healthcare
- Travel
- Salary
- Transfer
- Withdrawal
- Investment
- Insurance
- Subscription
- Other

Respond ONLY with the category name, nothing else."""

    user_prompt = f"Transaction data: {raw_data}"

    try:
        # Call Groq API with minimal prompt
        response = await ask_groq(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,  # Low temperature for consistent results
            max_tokens=20  # Short response needed
        )
        
        # Clean and return the category
        category = response.strip()
        return category
        
    except Exception as e:
        print(f"Error detecting category: {str(e)}")
        return "Other"  # Default fallback