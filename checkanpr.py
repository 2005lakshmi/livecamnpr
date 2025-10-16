import streamlit as st
import os
import json
import numpy as np
from PIL import Image
import face_recognition
#Successfully installed face_recognition_models-0.3.0
# === Setup ===
PROFILE_DIR = "profiles"
os.makedirs(PROFILE_DIR, exist_ok=True)

st.set_page_config(page_title="Face Profile Manager", layout="centered")
st.title("👤 Face Profile Manager")
st.caption("Create profiles, upload face photos, and log in via selfie")

# === Helper Functions ===
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

'''def create_embedding_from_photos(uploaded_files):
    embeddings = []
    for uploaded_file in uploaded_files:
        try:
            # Open image
            image = Image.open(uploaded_file)
            image = np.array(image.convert("RGB"))  # Ensure RGB

            # Detect face and encode
            face_encodings = face_recognition.face_encodings(image)
            if face_encodings:
                embeddings.append(face_encodings[0])
            else:
                st.warning(f"No face detected in {uploaded_file.name}")
        except Exception as e:
            st.error(f"Error processing {uploaded_file.name}: {str(e)}")
    
    if not embeddings:
        return None
    # Average all embeddings for robustness
    return np.mean(embeddings, axis=0)'''
def weighted_average_embedding(photos):
    embeddings = []
    weights = []
    for photo in photos:
        image = face_recognition.load_image_file(photo)
        face_locations = face_recognition.face_locations(image)
        if not face_locations:
            continue
        
        # Quality heuristic: larger face = better
        top, right, bottom, left = face_locations[0]
        face_size = (right - left) * (bottom - top)
        
        enc = face_recognition.face_encodings(image)[0]
        embeddings.append(enc)
        weights.append(face_size)  # Bigger face → higher weight
    
    return np.average(embeddings, axis=0, weights=weights)

# === Tabs ===
tab1, tab2, tab3 = st.tabs(["	Create Profile", "	Login", "	Manage Profiles"])

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

# === Tab 2: Login ===
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
                    # Process selfie
                    image = Image.open(selfie)
                    image = np.array(image.convert("RGB"))
                    face_encodings = face_recognition.face_encodings(image)
                    
                    if not face_encodings:
                        st.error("❌ No face detected in selfie!")
                    else:
                        selfie_embedding = face_encodings[0]
                        stored_embedding, meta = load_profile(selected_profile)
                        
                        # Compare faces
                        distance = face_recognition.face_distance([stored_embedding], selfie_embedding)[0]
                        threshold = 0.6  # Lower = stricter
                        
                        if distance < threshold:
                            st.success(f"✅ Welcome, **{selected_profile}**! (Confidence: {1-distance:.2f})")
                            st.session_state["logged_in"] = selected_profile
                        else:
                            st.error(f"❌ Face not recognized. Distance: {distance:.2f} (threshold: {threshold})")
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
