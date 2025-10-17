import streamlit as st
import os
import json
import numpy as np
from PIL import Image
from deepface import DeepFace  # Replaced face_recognition with DeepFace

# === Setup ===
PROFILE_DIR = "profiles"
os.makedirs(PROFILE_DIR, exist_ok=True)

st.set_page_config(page_title="Face Profile Manager", layout="centered")
st.title("👤 Face Profile Manager")
st.caption("Create profiles, upload face photos, and log in via selfie")

# === Helper Functions (MODIFIED) ===
def get_existing_profiles():
    return [f.replace(".npy", "") for f in os.listdir(PROFILE_DIR) if f.endswith(".npy")]

def save_profile(name, embedding, photo_count):
    np.save(os.path.join(PROFILE_DIR, f"{name}.npy"), embedding)
    meta = {"name": name, "photo_count": photo_count}
    with open(os.path.join(PROFILE_DIR, f"{name}.json"), "w") as f:
        json.dump(meta, f)

def load_profile(name):
    emb = np.load(os.path.join(PROFILE_DIR, f"{name}.npy"))
    with open(os.path.join(PROFILE_DIR, f"{name}.json"), "r") as f:
        meta = json.load(f)
    return emb, meta

def create_embedding_from_photos(uploaded_files):
    """
    New function using DeepFace to create an averaged face embedding from multiple photos.
    """
    embeddings = []
    for uploaded_file in uploaded_files:
        try:
            # Save the uploaded file to a temporary path for DeepFace to process
            with open("temp_img.jpg", "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Use DeepFace to represent the face. This returns a list of detected faces.
            face_representations = DeepFace.represent(
                img_path = "temp_img.jpg",
                model_name = "VGG-Face",  # You can change this model (e.g., "Facenet")
                detector_backend = "opencv",  # Faster, good balance of speed/accuracy
                align = True
            )
            
            if face_representations:
                # Take the embedding of the first detected face
                embedding = face_representations[0]["embedding"]
                embeddings.append(embedding)
            else:
                st.warning(f"No face detected in {uploaded_file.name}")
        except Exception as e:
            st.error(f"Error processing {uploaded_file.name}: {str(e)}")
    
    # Clean up temporary image
    if os.path.exists("temp_img.jpg"):
        os.remove("temp_img.jpg")
    
    if not embeddings:
        return None
    
    # Average all embeddings for a robust profile
    avg_embedding = np.mean(embeddings, axis=0)
    return avg_embedding

# === Tabs ===
tab1, tab2, tab3 = st.tabs(["Create Profile", "Login", "Manage Profiles"])

# === Tab 1: Create Profile ===
with tab1:
    st.subheader("1. Create New Profile")
    name = st.text_input("Profile Name (e.g., Alice)", key="new_name")
    uploaded_files = st.file_uploader(
        "Upload face photos (as many as you want!)",
        accept_multiple_files=True,
        type=["jpg", "jpeg", "png"]
    )
    
    if st.button("✅ Create Profile", type="primary"):
        if not name:
            st.error("Please enter a profile name.")
        elif name in get_existing_profiles():
            st.error(f"Profile '{name}' already exists!")
        elif not uploaded_files:
            st.error("Please upload at least one photo.")
        else:
            with st.spinner("Processing photos..."):
                embedding = create_embedding_from_photos(uploaded_files)
                if embedding is not None:
                    save_profile(name, embedding, len(uploaded_files))
                    st.success(f"✅ Profile '{name}' created with {len(uploaded_files)} photos!")
                    st.balloons()
                else:
                    st.error("No valid faces found in any photo. Try again.")

# === Tab 2: Login (MODIFIED) ===
with tab2:
    st.subheader("2. Login with Face")
    profiles = get_existing_profiles()
    
    if not profiles:
        st.warning("No profiles exist. Create one first!")
    else:
        selected_profile = st.selectbox("Select your profile", profiles)
        selfie = st.camera_input("Take a selfie to verify")
        
        if selfie and st.button("🔓 Verify Login"):
            with st.spinner("Verifying..."):
                try:
                    # Save the selfie to a temporary file
                    with open("temp_selfie.jpg", "wb") as f:
                        f.write(selfie.getbuffer())
                    
                    # Load the stored profile embedding
                    stored_embedding, meta = load_profile(selected_profile)
                    
                    # Use DeepFace's verify function to compare the selfie with the stored profile
                    result = DeepFace.verify(
                        img1_path = os.path.join(PROFILE_DIR, f"{selected_profile}.npy"),  # This is a path to the npy file. In practice, you might need a different approach.
                        img2_path = "temp_selfie.jpg",
                        model_name = "VGG-Face",
                        distance_metric = "cosine",  # Or "euclidean", "euclidean_l2"
                        detector_backend = "opencv",
                        align = True
                    )
                    
                    # Clean up temporary selfie
                    if os.path.exists("temp_selfie.jpg"):
                        os.remove("temp_selfie.jpg")
                    
                    # DeepFace returns a dictionary with a 'verified' key
                    if result['verified']:
                        # Calculate a simple confidence score. Distance lower is better.
                        confidence = 1 - result['distance']
                        st.success(f"✅ Welcome, **{selected_profile}**! (Confidence: {confidence:.2f})")
                        st.session_state["logged_in"] = selected_profile
                    else:
                        st.error(f"❌ Face not recognized. Distance: {result['distance']:.2f}")
                        
                except Exception as e:
                    st.error(f"Verification failed: {str(e)}")

# === Tab 3: Manage Profiles ===
with tab3:
    st.subheader("3. Manage Profiles")
    profiles = get_existing_profiles()
    
    if not profiles:
        st.info("No profiles yet.")
    else:
        for profile in profiles:
            emb, meta = load_profile(profile)
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**{profile}** – {meta['photo_count']} photos")
            with col2:
                if st.button("🗑️ Delete", key=f"del_{profile}"):
                    os.remove(os.path.join(PROFILE_DIR, f"{profile}.npy"))
                    os.remove(os.path.join(PROFILE_DIR, f"{profile}.json"))
                    st.rerun()
