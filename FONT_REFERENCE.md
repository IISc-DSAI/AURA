# Font Reference Guide for Streamlit

## Quick Font Examples

### System Fonts (No Loading Required)
```python
# Serif fonts
font-family: 'Georgia', serif;
font-family: 'Times New Roman', serif;

# Sans-serif fonts  
font-family: 'Arial', sans-serif;
font-family: 'Helvetica', sans-serif;
font-family: 'Verdana', sans-serif;

# Monospace
font-family: 'Courier New', monospace;

# Cursive (fancy)
font-family: 'Brush Script MT', cursive;
font-family: 'Lucida Handwriting', cursive;
```

### Google Fonts (Require Loading)

**Fancy/Script Fonts:**
- `Pacifico` - Casual script
- `Dancing Script` - Elegant script
- `Lobster` - Bold cursive
- `Great Vibes` - Elegant script
- `Satisfy` - Casual script
- `Kalam` - Handwriting style
- `Caveat` - Casual handwriting
- `Permanent Marker` - Bold marker style

**Bold/Display Fonts:**
- `Bebas Neue` - Bold condensed
- `Oswald` - Bold sans-serif
- `Righteous` - Bold display
- `Bangers` - Comic style
- `Fredoka One` - Rounded bold

**Elegant Fonts:**
- `Playfair Display` - Elegant serif
- `Cormorant Garamond` - Classic serif
- `Cinzel` - Decorative serif
- `Merriweather` - Readable serif

**Modern Fonts:**
- `Roboto` - Clean modern
- `Open Sans` - Friendly modern
- `Montserrat` - Geometric modern
- `Lato` - Humanist sans-serif
- `Poppins` - Geometric sans-serif

## How to Use Google Fonts

```python
# Step 1: Load the font
st.markdown("""
<link href='https://fonts.googleapis.com/css2?family=FontName&display=swap' rel='stylesheet'>
""", unsafe_allow_html=True)

# Step 2: Use it in your CSS
st.markdown("""
<style>
    .my-text {
        font-family: 'FontName', sans-serif;
    }
</style>
""", unsafe_allow_html=True)
```

## Example: Multiple Fancy Fonts

```python
# Load multiple fonts at once
st.markdown("""
<link href='https://fonts.googleapis.com/css2?family=Pacifico&family=Dancing+Script:wght@700&family=Lobster&family=Great+Vibes&display=swap' rel='stylesheet'>
""", unsafe_allow_html=True)

# Then use any of them:
# font-family: 'Pacifico', cursive;
# font-family: 'Dancing Script', cursive;
# font-family: 'Lobster', cursive;
# font-family: 'Great Vibes', cursive;
```

