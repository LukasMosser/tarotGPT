import streamlit as st
import random
import json
import openai
from PIL import Image
from io import BytesIO
import base64
from pydantic import BaseModel, Field, ValidationError
from typing import List
from PIL import Image, ImageOps
import requests
import json


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


# Function to fetch the tarot deck from a Gist URL and parse it
def fetch_tarot_deck_from_gist(gist_url):
    try:
        # Make a GET request to the Gist URL
        response = requests.get(gist_url)
        
        # Check if the response is valid
        if response.status_code == 200:
            try:
                # Parse the JSON content from the response
                tarot_deck_json = response.json()
                
                # Parse the JSON into the ImagedTarotDeck model
                tarot_deck = ImagedTarotDeck(**tarot_deck_json)
                return tarot_deck
            except json.JSONDecodeError:
                st.error("Error: The content retrieved from the URL is not valid JSON.")
                return None
            except ValidationError as e:
                st.error(f"Validation Error: {str(e)}")
                return None
        else:
            st.error(f"Failed to fetch data from Gist. Status code: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error fetching tarot deck: {str(e)}")
        return None

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

    with st.expander("About", expanded=False):
        st.markdown(
            """
            Welcome to the **Tarot GPT Reader**, an interactive tarot reading experience powered by GPT and designed using the ancient Keltic Cross method. This application allows you to upload a custom tarot deck and perform a detailed reading with both upright and reversed card interpretations.

            ## How to Use the Application

            ### Step 0: Fetch a Tarot Deck from Gist
            - **Upload your custom tarot deck to a Gist**: Create a JSON file containing 78 tarot cards with descriptions, meanings, and images. Upload the file to a Gist and enter the Gist URL in the provided text box.
            - **Fetch Deck**: The application will fetch the tarot deck from the Gist URL and display the cards for selection.

            ### Step 1: Choose the Querent's Card
            - **Court Card Selection**: In this step, you select a card to represent the querent (the person receiving the reading). Typically, this will be a court card such as a **Page**, **Knight**, **Queen**, or **King**, which best represents the querent’s personality or physical characteristics.
            - **Selection**: Use the dropdown menu to choose the appropriate court card from the Minor Arcana.
            - **Card Display**: After selecting the querent's card, the application will display the card's image and description.

            ### Step 2: Enter the Querent's Question
            - **Input**: In this step, the querent should silently or aloud ask a meaningful and important question. The question should be entered in the provided text box.
            - **Purpose**: This question will guide the interpretation of the cards during the reading.

            ### Step 3: Shuffle and Draw Cards for the Keltic Cross Layout
            - **Card Drawing**: Once the querent’s card is selected and the question is entered, click the **Shuffle and Draw Cards** button to begin the reading.
            - **Automatic Drawing**: The application will randomly shuffle and draw 10 cards for the Keltic Cross spread, excluding the querent's card.
            - **Card Reversal**: Approximately 50% of the drawn cards will be reversed, which affects their interpretation.
            - **Card Layout**: The Keltic Cross layout will be displayed, with:
            - **This Covers**: The central card representing the general situation.
            - **This Crosses**: The second card representing opposing forces (rotated 90 degrees).
            - **This Is Beneath**: The foundation of the situation.
            - **This Is Behind**: Past influences.
            - **This Crowns**: Possible outcomes.
            - **This Is Before**: Immediate future influences.
            - **What the Querent Fears**: Querent's fears or anxieties.
            - **Family Opinion**: External influences from family or community.
            - **Hopes**: Querent's hopes and aspirations.
            - **Final Outcome**: The final result or answer to the querent's question.

            ### Step 4: Card Interpretations
            - **Interpretations**: After the cards are drawn, the application will generate interpretations for each card based on its position in the spread, its orientation (upright or reversed), and the querent's question.
            - **Display**: Each card's name, position, orientation, and generated interpretation will be displayed alongside its image.

            ### Step 5: Final Summary
            - **Summary**: After all cards are interpreted, a final summary will be generated to provide a cohesive overview of the reading in relation to the querent's question.
            - **Insight**: This summary will synthesize the key messages from the reading and offer insights to the querent.

            ---

            ## Example Usage

            - **Upload Deck**: Start by downloading a custom tarot deck JSON file containing 78 cards with descriptions, meanings, and images.
            - **Select Querent's Card**: Choose a court card that best represents the querent from the dropdown list.
            - **Ask a Question**: Enter the querent's question into the text box for the reading.
            - **Generate Spread**: Click the **Shuffle and Draw Cards** button to generate the Keltic Cross spread. Each card will be interpreted based on its position in the spread, orientation, and relevance to the querent's question.
            - **Review Summary**: Read the final summary for an overview of the querent's situation and possible outcomes.

            ---

            ## Notes:
            - This application leverages GPT-4 to provide interpretations for each card in relation to the querent's question, creating a personalized reading experience.
            - The tarot deck must be uploaded from a json that is downloaded from a github gist.
            - The Keltic Cross layout provides a detailed and structured tarot reading that considers various aspects of the querent's situation, including past influences, future possibilities, external factors, and internal fears.

            Enjoy your tarot reading experience!

            """)
        
    # Step 0: Enter Gist URL
    st.header("Step 0: Enter Gist URL for Tarot Deck JSON")
    gist_url = st.text_input("Enter the Gist URL for the Tarot Deck JSON:")

    if gist_url:
        tarot_deck = fetch_tarot_deck_from_gist(gist_url)
        
        if tarot_deck:
            st.success("Tarot deck fetched successfully!")
        
            try:
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
                        with st.expander(card.name):
                            st.write(f"**Description**: {card.description}")
                            st.write(f"**Divinatory Meaning**: {card.divinatory_meaning}")
                            st.write(f"**Reversed Meaning**: {card.reversed}")
                            st.write(f"**Physical Description**: {card.physical_description}")
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
