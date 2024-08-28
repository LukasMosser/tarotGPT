import streamlit as st
import json
from PIL import Image
from io import BytesIO
import base64
from pydantic import BaseModel, Field, ValidationError
from typing import List
import requests
import math
import os
import img2pdf
import uuid

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
    
# Function to decode the base64 image and display it, rotated if reversed
def display_card_image(card: ImagedArcana, reversed: bool):
    image_data = base64.b64decode(card.image_base64)
    image = Image.open(BytesIO(image_data))
    if reversed:
        image = image.rotate(180)
    st.image(image, caption=card.name, use_column_width=True)

if "deck_pdf" not in st.session_state:
    st.session_state["deck_pdf"] = None

if "tarot_deck" not in st.session_state:
    st.session_state["tarot_deck"] = None

if "major_arcana_images" not in st.session_state:
    st.session_state["major_arcana_images"] = None 

if "minor_arcana_images" not in st.session_state:
    st.session_state["minor_arcana_images"] = None

if "deck_pdf_path" not in st.session_state:
    st.session_state["deck_pdf_path"] = None

def create_card_grids(card_images, output_dir="output_cards"):
    # A4 dimensions in pixels at 300 DPI (for high-quality print)
    a4_width_px = int(21.0 / 2.54 * 300)
    a4_height_px = int(29.7 / 2.54 * 300)
    
    # Card size in pixels at 300 DPI
    card_width_px = int(6.4 / 2.54 * 300)
    card_height_px = int(8.9 / 2.54 * 300)
    
    # Margins and padding
    margin_px = 50  # Margin from the edge of the page
    padding_px = 20  # Space between cards
    
    # Calculate the number of cards per row and column
    cards_per_row = (a4_width_px - 2 * margin_px + padding_px) // (card_width_px + padding_px)
    cards_per_col = (a4_height_px - 2 * margin_px + padding_px) // (card_height_px + padding_px)
    
    # Calculate how many cards fit per page
    cards_per_page = cards_per_row * cards_per_col
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    num_pages = math.ceil(len(card_images) / cards_per_page)
    image_paths = []

    for page in range(num_pages):
        # Create a new blank A4 image
        a4_image = Image.new("RGB", (a4_width_px, a4_height_px), "white")
        
        # Determine the slice of cards for this page
        start_idx = page * cards_per_page
        end_idx = min((page + 1) * cards_per_page, len(card_images))
        current_cards = card_images[start_idx:end_idx]
        
        for idx, card_image in enumerate(current_cards):
            # Calculate position of the card in the grid
            row = idx // cards_per_row
            col = idx % cards_per_row
            x = margin_px + col * (card_width_px + padding_px)
            y = margin_px + row * (card_height_px + padding_px)

            # Resize and paste the card onto the A4 image
            card_image_resized = card_image.resize((card_width_px, card_height_px), Image.Resampling.LANCZOS)
            a4_image.paste(card_image_resized, (x, y))
        
        # Save the resulting image for this page
        output_path = os.path.join(output_dir, f"cards_page_{page + 1}.png")
        a4_image.save(output_path, "PNG")
        image_paths.append(output_path)
    
    # Generate a unique filename using UUID
    unique_filename = f"{uuid.uuid4()}.pdf"
    pdf_path = os.path.join(output_dir, unique_filename)
    
    # Convert the PNGs to a single PDF file
    pdf_bytes = img2pdf.convert(image_paths)
    
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)
    
    # Return the PDF path for download
    return pdf_path

def create_major_arcana_grid(card_images, output_path="major_arcana_grid.png"):
    # Instagram-friendly dimensions (1080x1080 pixels or similar)
    image_size_px = 1080  # Example square size, adjust as needed
    card_width_px = image_size_px // 6  # Adjust grid size to fit cards
    card_height_px = card_width_px * 1.39  # Keeping aspect ratio 6.4 x 8.9 cm
    
    # Create a blank image for the grid
    grid_image = Image.new("RGB", (image_size_px, image_size_px), "white")
    
    # Arrange cards in a 6x4 grid
    for idx, card_image in enumerate(card_images):
        if idx >= 22:
            break  # Stop if we've placed all Major Arcana cards

        row = idx // 6
        col = idx % 6
        x = int(col * card_width_px)
        y = int(row * card_height_px)
        
        # Resize and paste the card onto the grid image
        card_image_resized = card_image.resize((int(card_width_px), int(card_height_px)), Image.Resampling.LANCZOS)
        grid_image.paste(card_image_resized, (x, y))
    
    # Save the grid image
    grid_image.save(output_path, "PNG")
    return output_path

def create_minor_arcana_grid(card_images, output_path="minor_arcana_grid.png"):
    # Instagram-friendly dimensions (1080x1080 pixels or similar)
    image_width_px = 1080  # Example width, adjust as needed
    card_width_px = image_width_px // 14  # 14 cards per row
    card_height_px = card_width_px * 1.39  # Keeping aspect ratio 6.4 x 8.9 cm
    
    # Total height required for 4 rows
    image_height_px = card_height_px * 4
    
    # Create a blank image for the grid
    grid_image = Image.new("RGB", (int(image_width_px), int(image_height_px)), "white")
    
    # Arrange cards in 4 rows (one row per suit)
    for idx, card_image in enumerate(card_images):
        row = idx // 14
        col = idx % 14
        x = int(col * card_width_px)
        y = int(row * card_height_px)
        
        # Resize and paste the card onto the grid image
        card_image_resized = card_image.resize((int(card_width_px), int(card_height_px)), Image.Resampling.LANCZOS)
        grid_image.paste(card_image_resized, (x, y))
    
    # Save the grid image
    grid_image.save(output_path, "PNG")
    return output_path


def download_pdf(pdf_path):
    with open(pdf_path, "rb") as f:
        pdf_data = f.read()
    st.download_button(label="Download Cards PDF", data=pdf_data, file_name=os.path.basename(pdf_path), mime="application/pdf")


st.title("🔎 Tarot Card Deck Explorer")
st.markdown("""This app allows you to explore a Tarot Card Deck fetched from a Gist URL.
            Please enter the Gist URL for the Tarot Deck JSON to get started.""")

gist_url = st.text_input("Enter the Gist URL for the Tarot Deck JSON:")

if gist_url:
    tarot_deck = fetch_tarot_deck_from_gist(gist_url)
    st.session_state["tarot_deck"] = tarot_deck

if st.session_state["tarot_deck"] is not None:
    st.success("Tarot deck fetched successfully!")

    if st.button("Generate Major Arcana Grid PNG"):
        major_arcana_images = []
        for card in tarot_deck.major_arcana:
            image_data = base64.b64decode(card.image_base64)
            image = Image.open(BytesIO(image_data))
            major_arcana_images.append(image)
        
        major_arcana_path = create_major_arcana_grid(major_arcana_images)
        st.session_state["major_arcana_images"] = major_arcana_path

    if st.session_state["major_arcana_images"] is not None:
        st.image(st.session_state["major_arcana_images"], caption="Major Arcana Grid", use_column_width=True)
        with open(st.session_state["major_arcana_images"], "rb") as f:
            uuid_number = uuid.uuid4()
            st.download_button(label="Download Major Arcana Grid PNG", data=f, file_name=f"major_arcana_grid_{uuid_number}.png", mime="image/png")

    if st.button("Generate Minor Arcana Grid PNG"):
        minor_arcana_images = []
        for card in tarot_deck.minor_arcana:
            image_data = base64.b64decode(card.image_base64)
            image = Image.open(BytesIO(image_data))
            minor_arcana_images.append(image)
        
        minor_arcana_path = create_minor_arcana_grid(minor_arcana_images)
        st.session_state["minor_arcana_images"] = minor_arcana_path

    if st.session_state["minor_arcana_images"] is not None:
        st.image(st.session_state["minor_arcana_images"], caption="Minor Arcana Grid", use_column_width=True)
        with open(st.session_state["minor_arcana_images"], "rb") as f:
            uuid_number = uuid.uuid4()
            st.download_button(label="Download Minor Arcana Grid PNG", data=f, file_name=f"minor_arcana_grid_{uuid_number}.png", mime="image/png")

    if st.button("Generate Tarot Cards PDF"):
        card_images = []
        for card in tarot_deck.major_arcana + tarot_deck.minor_arcana:
            image_data = base64.b64decode(card.image_base64)
            image = Image.open(BytesIO(image_data))
            card_images.append(image)

        pdf_path = create_card_grids(card_images)
        st.session_state["deck_pdf_path"] = pdf_path
    
    if st.session_state["deck_pdf_path"] is not None:
        download_pdf(pdf_path)


    st.header("Major Arcana")
    for card in tarot_deck.major_arcana:
        with st.expander(card.name):
            st.write(f"Description: {card.description}")
            st.write(f"Divinatory Meaning: {card.divinatory_meaning}")
            st.write(f"Reversed Meaning: {card.reversed}")
            st.write(f"Physical Description: {card.physical_description}")
            display_card_image(card, reversed=False)

    st.header("Minor Arcana")
    for card in tarot_deck.minor_arcana:
        with st.expander(card.name):
            st.write(f"Description: {card.description}")
            st.write(f"Divinatory Meaning: {card.divinatory_meaning}")
            st.write(f"Reversed Meaning: {card.reversed}")
            st.write(f"Physical Description: {card.physical_description}")
            display_card_image(card, reversed=False)

