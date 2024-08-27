import streamlit as st
import random
import json
import openai
from PIL import Image
from io import BytesIO
import base64
from pydantic import BaseModel, Field
from typing import List
from PIL import Image, ImageDraw, ImageFont, ImageOps

# Define Pydantic models
class Arcana(BaseModel):
    name: str = Field(..., description="The name of the tarot arcana")
    description: str = Field(..., description="The description of the tarot arcana")
    divinatory_meaning: str = Field(..., description="The divinatory meaning of the tarot arcana")
    reversed: str = Field(..., description="The reversed divinatory meaning of the tarot arcana")

class ImagedArcana(Arcana):
    physical_description: str = Field(..., description="The physical description of the tarot card")
    image_base64: str = Field(..., description="The base64 encoded image of the tarot card")

class ImagedTarotDeck(BaseModel):
    major_arcana: List[ImagedArcana] = Field(..., description="The 22 Major Arcana of a Tarot Deck")
    minor_arcana: List[ImagedArcana] = Field(..., description="The 56 Minor Arcana of a Tarot Deck")

# Load tarot deck from JSON and parse with Pydantic models
def load_tarot_deck(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    tarot_deck = ImagedTarotDeck(**data)
    return tarot_deck

# Function to decode the base64 image and display it, rotated if reversed
def display_card_image(card: ImagedArcana, reversed: bool):
    image_data = base64.b64decode(card.image_base64)
    image = Image.open(BytesIO(image_data))
    if reversed:
        image = image.rotate(180)
    st.image(image, caption=card.name, use_column_width=True)

# Shuffle the deck and draw cards (excluding already drawn cards), with 50:50 reversed logic
def draw_cards(deck, num_cards, excluded_cards):
    available_cards = [card for card in (deck.major_arcana + deck.minor_arcana) if card not in excluded_cards]
    random.shuffle(available_cards)
    drawn_cards = available_cards[:num_cards]
    
    # Assign roughly 50% of cards as reversed
    card_states = [{'card': card, 'reversed': random.choice([True, False])} for card in drawn_cards]
    
    return card_states

# Generate the tarot deck description for the system prompt
def generate_deck_description(tarot_deck):
    deck_description = "This is a custom tarot deck. Below are the descriptions of each card:\n\n"
    for card in tarot_deck.major_arcana + tarot_deck.minor_arcana:
        deck_description += f"Card Name: {card.name}\n"
        deck_description += f"Description: {card.description}\n"
        deck_description += f"Divinatory Meaning: {card.divinatory_meaning}\n"
        deck_description += f"Reversed Meaning: {card.reversed}\n\n"
    return deck_description

# Call GPT-4 for card interpretation
def interpret_card(card: ImagedArcana, querent_question: str, position: str, reversed: bool, deck_description: str):
    orientation = "reversed" if reversed else "upright"
    prompt = f"Interpret the tarot card {card.name} in relation to the querent's question: '{querent_question}'. The card is in the position: {position}, and it is {orientation}. Here is the divinatory meaning: {card.divinatory_meaning}. Reversed: {card.reversed}."
    
    system_prompt = f"{deck_description}\nYou are a tarot reader following the ancient Celtic method."
    
    client = openai.Client()
    response = client.chat.completions.create(
        model="gpt-4o-2024-08-06",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    )
    
    return response.choices[0].message.content.strip()

# Generate a final summary using GPT-4
def generate_summary(querent_question: str, interpretations: List[str], deck_description: str):
    summary_prompt = f"Given the following tarot card interpretations and the querent's question: '{querent_question}', create a cohesive summary that ties everything together in relation to the querent's question:\n\n"
    
    for idx, interpretation in enumerate(interpretations):
        summary_prompt += f"Interpretation {idx+1}: {interpretation}\n"
    
    summary_prompt += "\nPlease summarize the key messages and insights for the querent."
    
    system_prompt = f"{deck_description}\nYou are a tarot reader following the ancient Celtic method."
    
    client = openai.Client()
    response = client.chat.completions.create(
        model="gpt-4o-2024-08-06",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": summary_prompt}
        ]
    )
    
    return response.choices[0].message.content.strip()

# Function to decode the base64 image and convert to PIL image
def get_card_image(card: ImagedArcana, reversed: bool):
    image_data = base64.b64decode(card.image_base64)
    image = Image.open(BytesIO(image_data))
    if reversed:
        image = ImageOps.flip(ImageOps.mirror(image))
    return image

# Function to draw the Keltic Cross spread
def draw_keltic_cross(cards):
    # Create a blank white canvas
    canvas = Image.new('RGB', (1000, 1000), (255, 255, 255))  # Increased size for spacing
    
    # Positions for each card in the Keltic Cross layout
    positions = {
        # Left side: cross layout
        1: (350, 450),  # This Covers (center)
        2: (325, 475),  # This Crosses (center, rotated 90 degrees)
        3: (350, 700),  # This Is Beneath (below the center)
        4: (100, 450),  # This Is Behind (left of the center)
        5: (350, 200),  # This Crowns (above the center)
        6: (600, 450),  # This Is Before (right of the center)
        
        # Right side: vertical layout
        7: (800, 750),  # What He Fears (bottom of the vertical stack)
        8: (800, 550),  # Family Opinion (above What He Fears)
        9: (800, 350),  # Hopes (above Family Opinion)
        10: (800, 150)  # Final Outcome (top of the vertical stack)
    }
    
    # Draw each card in the Keltic Cross spread
    for idx, card_data in enumerate(cards):
        card_image = get_card_image(card_data['card'], card_data['reversed'])
        
        # Resize card image
        card_image = card_image.resize((120, 180))
        
        # Special handling for Card 2 ("This Crosses")
        if idx == 1:
            card_image = card_image.rotate(90, expand=True)  # Rotate "This Crosses" card by 90 degrees
        
        # Paste the card on the canvas
        canvas.paste(card_image, positions[idx + 1], card_image.convert('RGBA'))
    
    # Convert the canvas to a format that can be rendered in Streamlit
    buffered = BytesIO()
    canvas.save(buffered, format="PNG")
    img_data = buffered.getvalue()
    
    return img_data

# Streamlit application
def tarot_reading_app():
    st.title("Tarot GPT Reading with the Keltic Method")
    # Step 0: Upload tarot deck JSON file
    st.header("Step 0: Upload Tarot Deck JSON File")
    uploaded_file = st.file_uploader("Upload Tarot Deck JSON File", type="json")

    if uploaded_file is not None:
        # Read the uploaded JSON file
        file_contents = uploaded_file.read()
        
        try:
            # Decode the JSON file
            tarot_deck = load_tarot_deck(file_contents)
            deck_description = generate_deck_description(tarot_deck)
            
            # Continue with the rest of the application
            st.success("Tarot deck uploaded successfully!")

            # Step 1: Querent's card selection
            st.header("Step 1: Choose a card to represent the Querent")
            
            # Filter for Court Cards (assuming they're all in the Minor Arcana)
            court_cards = [card for card in tarot_deck.minor_arcana if "Page" in card.name or "Knight" in card.name or "Queen" in card.name or "King" in card.name]
            
            querent_card_name = st.selectbox(
                "Select the card that best represents the Querent:",
                [card.name for card in court_cards]
            )
            
            querent_card = next((card for card in court_cards if card.name == querent_card_name), None)
            
            if querent_card:
                # Display the Querent card separately
                st.subheader(f"Querent's Card: {querent_card.name}")
                display_card_image(querent_card, reversed=False)
                st.write(f"**Description:** {querent_card.physical_description}")
            
            # Step 2: Input Querent's question
            querent_question = st.text_input("Enter your question:", "")
            
            # Button to start the reading
            if st.button("Shuffle and Draw Cards"):
                # Initialize excluded cards list with the Querent's card
                excluded_cards = [querent_card]
                
                # Draw 10 cards for Keltic Spread (excluding the Querent's card)
                drawn_cards = draw_cards(tarot_deck, 10, excluded_cards)
                
                # The first card is for "This Covers", the second is for "This Crosses"
                covers_card = drawn_cards.pop(0)
                crosses_card = drawn_cards.pop(0)
                
                # Display the Keltic Cross layout with card images
                st.header("Keltic Cross Layout")
                
                # Pass the first two cards separately and then the rest
                keltic_cross_image = draw_keltic_cross([covers_card, crosses_card] + drawn_cards)
                st.image(keltic_cross_image, caption="Keltic Cross Layout", use_column_width=True)

                # Positions for Keltic Spread
                positions = ["This Covers", "This Crosses", "This Is Beneath", "This Is Behind", 
                            "This Crowns", "This Is Before", "What The Querent Fears", 
                            "Family Opinion", "Hopes", "Final Outcome"]
                
                # Store interpretations for summary
                interpretations = []
                
                # Display interpretations for the Keltic Cross cards
                for idx, card_data in enumerate([covers_card, crosses_card] + drawn_cards):
                    card = card_data['card']
                    reversed = card_data['reversed']
                    st.subheader(f"Position {positions[idx]}: {card.name} ({'Reversed' if reversed else 'Upright'})")
                    display_card_image(card, reversed)
                    interpretation = interpret_card(card, querent_question, positions[idx], reversed, deck_description)
                    st.write(interpretation)
                    interpretations.append(interpretation)
                
                # Generate a final summary based on all interpretations
                st.subheader("Final Summary")
                summary = generate_summary(querent_question, interpretations, deck_description)
                st.write(summary)
        except Exception as e:
            st.error(f"Error loading tarot deck: {str(e)}")

# Run the Streamlit app
if __name__ == "__main__":
    tarot_reading_app()
