import streamlit as st
import openai
from pydantic import BaseModel, Field, ConfigDict
from typing import List
import base64
import uuid
import modal

if 'deck' not in st.session_state:
    st.session_state.deck = None

# Initialize session state for custom arcana list
if 'custom_arcana_list' not in st.session_state:
    st.session_state.custom_arcana_list = []

# Define Pydantic models for Tarot Deck
class Arcana(BaseModel):
    name: str = Field(..., description="The name of the tarot arcana")
    description: str = Field(..., description="The description of the tarot arcana")
    divinatory_meaning: str = Field(..., description="The divinatory meaning of the tarot arcana")
    reversed: str = Field(..., description="The reversed divinatory meaning of the tarot arcana")

class TarotDeck(BaseModel): 
    major_arcana: List[Arcana] = Field(..., description="The 22 Major Arcana of a Tarot Deck")
    minor_arcana: List[Arcana] = Field(..., description="The 56 Minor Arcana of a Tarot Deck")

class ImagedArcana(Arcana):
    physical_description: str = Field(..., description="The physical description of the tarot card")
    image_base64: str = Field(..., description="The base64 encoded image of the tarot card")

class ImagedTarotDeck(BaseModel):
    major_arcana: List[ImagedArcana] = Field(..., description="The 22 Major Arcana of a Tarot Deck")
    minor_arcana: List[ImagedArcana] = Field(..., description="The 56 Minor Arcana of a Tarot Deck")

# Helper function to display the image from base64
def display_image(image_base64, width=300):
    image_data = base64.b64decode(image_base64)
    st.image(image_data, width=width)

# Function to call GPT-4 and generate card descriptions and images
def generate_card(client: openai.Client, arcana: Arcana):
    completion = client.chat.completions.create(
        model="gpt-4o-2024-08-06",
        messages=[
            {"role": "system", "content": "Generate a short description of the physical tarot card that exemplifies the given arcana. Not more than 50 words."},
            {"role": "user", "content": f"Arcana Name: {arcana.name} Description: {arcana.description}, Divinatory Meaning: {arcana.divinatory_meaning}, Reversed: {arcana.reversed}"},
        ],
        max_tokens=50,
    )
    description = completion.choices[0].message.content
    description = description + f" The card says {arcana.name} on the card."

    cls = modal.Cls.lookup("tarotGPT", "Model")
    obj = cls()  # You can pass any constructor arguments here
    response = obj.inference.remote(prompt=description)

    image_base64 = base64.b64encode(response).decode("utf-8")

    return description, image_base64

# Streamlit app
def tarot_app():
    client = openai.Client()
    
    st.title("Custom Tarot Deck Generator")

    with st.expander("About", expanded=False):
        st.markdown("""
        Welcome to the **Custom Tarot Deck Generator**! This application allows you to create a fully personalized tarot deck based on your chosen theme. You can generate all 78 cards, including 22 Major Arcana and 56 Minor Arcana, with custom descriptions and card images.

        ## How to Use the Application

        ### Step 1: Enter a Theme for Your Tarot Deck
        - **Input**: At the top of the application, there is a text input box labeled *Enter a theme for your custom Tarot deck*.
        - **Prompt**: Enter a creative theme or concept for your deck. This could be anything from "Ancient Mythology" to "Space Exploration" or even something abstract like "Emotional Growth."

        ### Step 2: Generate the Deck
        - **Button**: After entering your theme, click the **Generate Deck** button.
        - **Deck Creation**: Once the deck is generated, you will see the Major Arcana and Minor Arcana cards listed. You can expand each card to view its:
        - Name
        - Description
        - Divinatory Meaning
        - Reversed Meaning

        ### Step 3: Generate Tarot Card Images
        - **Button**: After reviewing your deck, click the **Generate Deck Card Images** button.
        - **Progress Bar**: A progress bar will appear, indicating the status of generating each card's physical description and image.
        - **Live Rendering**: As each card is generated, the image and description will be displayed in real-time below the progress bar.

        ### Step 4: Review the Generated Cards
        - **Major Arcana**: The generated Major Arcana cards will be shown first. You can expand each card to view its:
        - Name
        - Description
        - Divinatory Meaning
        - Reversed Meaning
        - Physical Card Description
        - Image (rendered directly in the app)
        
        - **Minor Arcana**: The generated Minor Arcana cards will be shown next with the same details and image rendering.

        ### Step 5: Download the Custom Deck
        - **Download**: Once all the cards are generated, you can download the entire deck as a JSON file.
        - **Button**: Click the **Download Deck JSON** button to save the JSON file to your computer.
        
        This file will include the detailed descriptions and images of all 78 tarot cards from your custom deck.

        ## Example Usage

        - **Theme**: You might enter a theme like "Oceanic Adventures."
        - **Deck Generation**: The application will create a tarot deck with cards that match the theme, like "The Lighthouse" for the Major Arcana or "The Wave" as part of the custom suits in the Minor Arcana.
        - **Image Generation**: The application will generate images based on the card descriptions, like a card depicting an underwater castle or a majestic sea creature.
        - **Download**: Finally, you can download the JSON file of your ocean-themed tarot deck for future use.

        ## Notes:
        - The application integrates GPT-4 to generate card descriptions based on the theme you provide.
        - Each card's image is generated dynamically based on the descriptions, which are influenced by your theme.
        - The final JSON file includes all card details, which can be used for future applications or as a personalized tarot deck.

        Enjoy creating your custom tarot deck!
                    
    """)

    
    # User input for deck theme
    theme_prompt = st.text_input("Enter a theme for your custom Tarot deck:")
    
    # Button to trigger deck generation
    if st.button("Generate Deck"):
        if theme_prompt:

            # Store the deck in session state to persist across reruns
            completion = client.beta.chat.completions.parse(
                model="gpt-4o-2024-08-06",
                messages=[
                    {"role": "system", "content": "Generate a custom tarot deck based on the theme provided. Remember to include 22 major and 56 minor arcana. The minor arcana should follow four custom suits. Each suit should have an Ace, the Two, the Three, the Four, the Five, the Six, the Seven, the Eight, the Nine, the Ten, the Page, the Knight, the Queen, and the King of the suit."},
                    {"role": "user", "content": f"Theme: {theme_prompt}"},
                ],
                response_format=TarotDeck
            )
            
            st.session_state.deck = completion.choices[0].message.parsed

    if st.session_state.deck is not None:
        deck = st.session_state.deck

        # Major Arcana
        st.title("Major Arcana")
        for arcana in deck.major_arcana:
            with st.expander(arcana.name):
                st.markdown(f"**Description**: {arcana.description}")
                st.markdown(f"**Divinatory Meaning**: {arcana.divinatory_meaning}")
                st.markdown(f"**Reversed Meaning**: {arcana.reversed}")

        # Minor Arcana
        st.title("Minor Arcana")
        for arcana in deck.minor_arcana:
            with st.expander(arcana.name):
                st.markdown(f"**Description**: {arcana.description}")
                st.markdown(f"**Divinatory Meaning**: {arcana.divinatory_meaning}")
                st.markdown(f"**Reversed Meaning**: {arcana.reversed}")

        if st.button("Generate Deck Card Images"):
            # Prepare progress bar and text
            total_cards = len(deck.major_arcana) + len(deck.minor_arcana)
            progress_bar = st.progress(0)
            progress_text = st.empty()

            # Generate deck card by card
            for idx, arcana in enumerate(deck.major_arcana + deck.minor_arcana):
                # Update progress bar and progress text
                progress_percent = (idx + 1) / total_cards
                progress_bar.progress(progress_percent)
                progress_text.text(f"Generating card {idx + 1} of {total_cards}")

                # Generate card description and image
                description, img_base64 = generate_card(client, arcana)
                
                # Create custom arcana with image and description
                custom_arcana = ImagedArcana(
                    name=arcana.name,
                    description=arcana.description,
                    divinatory_meaning=arcana.divinatory_meaning,
                    reversed=arcana.reversed,
                    physical_description=description,
                    image_base64=img_base64
                )
                st.session_state.custom_arcana_list.append(custom_arcana)

                # Display the generated card
                st.image(base64.b64decode(img_base64), caption=f"{arcana.name}")

            # Create a new custom tarot deck
            custom_deck = ImagedTarotDeck(
                major_arcana=st.session_state.custom_arcana_list[:22],
                minor_arcana=st.session_state.custom_arcana_list[22:]
            )

            # Major Arcana
            st.title("Major Arcana")
            for arcana in custom_deck.major_arcana:
                with st.expander(arcana.name):
                    st.markdown(f"**Description**: {arcana.description}")
                    st.markdown(f"**Divinatory Meaning**: {arcana.divinatory_meaning}")
                    st.markdown(f"**Reversed Meaning**: {arcana.reversed}")
                    st.markdown(f"**Physical Card Description**: {arcana.physical_description}")
                    display_image(arcana.image_base64)

            # Minor Arcana
            st.title("Minor Arcana")
            for arcana in custom_deck.minor_arcana:
                with st.expander(arcana.name):
                    st.markdown(f"**Description**: {arcana.description}")
                    st.markdown(f"**Divinatory Meaning**: {arcana.divinatory_meaning}")
                    st.markdown(f"**Reversed Meaning**: {arcana.reversed}")
                    st.markdown(f"**Physical Card Description**: {arcana.physical_description}")
                    display_image(arcana.image_base64)

            # Convert the custom deck to JSON
            deck_json = custom_deck.json()

            # Provide download link for JSON deck file
            st.success("Deck generation completed!")
            st.download_button(
                label="Download Deck JSON",
                data=deck_json,
                file_name=f"custom_tarot_deck_{uuid.uuid4()}.json",
                mime="application/json"
            )

if __name__ == "__main__":
    tarot_app()
