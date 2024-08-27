import streamlit as st

st.set_page_config(
    page_title="TarotGPT",
    page_icon="🧙",
)

st.title("Welcome to TarotGPT! 👋")

st.sidebar.success("Select deck creation or tarot reading app")

st.markdown("""
# Custom Tarot Deck Creator and Reader

Welcome to the **Custom Tarot Deck Creator and Reader**! This application suite allows you to both design your own custom tarot deck and perform detailed tarot readings using the ancient Keltic Cross method.

- **Tarot Deck Creator**: Craft a personalized 78-card tarot deck by choosing a theme. Generate unique descriptions and images for each card, and download your custom deck as a JSON file for future use.

- **Tarot Reader**: Upload your custom tarot deck and perform an insightful reading. The reader app uses GPT to interpret both upright and reversed cards, providing in-depth insights into the querent's question using the Keltic Cross layout.

Explore the mystical world of tarot with your very own deck and uncover hidden insights through detailed readings!

""")