import streamlit as st
import os
import json
import numpy as np
from PIL import Image
from deepface import DeepFace
from scipy.spatial.distance import cosine
import tempfile

# === Setup ===
PROFILE_DIR = "profiles"
os.makedirs(PROFILE_DIR, exist_ok=True)

st.set_page_config(page_title="Face Profile Manager", layout="centered")
st.title("👤 Face Profile Manager")
st.caption("Create profiles, upload face photos, and log in via selfie (powered by DeepFace)")

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

def create_embedding_from_photos(uploaded_files):
    embeddings = []
    for uploaded_file in uploaded_files:
        try:
            # Save to temp file (DeepFace needs file path)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name

            # Use ArcFace (most accurate)
            embedding_objs = DeepFace.represent(
                img_path=tmp_path,
                model_name="ArcFace",
                enforce_detection=True,
                detector_backend="opencv"  # faster, no GPU needed
            )
            if embedding_objs:
                embeddings.append(embedding_objs[0]["embedding"])
            else:
                st.warning(f"No face detected in {uploaded_file.name}")
            os.unlink(tmp_path)
        except Exception as e:
            st.error(f"Error processing {uploaded_file.name}: {str(e)}")
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    if not embeddings:
        return None
    return np.mean(embeddings, axis=0)

def verify_selfie(selfie_bytes, stored_embedding):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        tmp.write(selfie_bytes)
        tmp_path = tmp.name

    try:
        embedding_objs = DeepFace.represent(
            img_path=tmp_path,
            model_name="ArcFace",
            enforce_detection=True,
            detector_backend="opencv"
        )
        if not embedding_objs:
            os.unlink(tmp_path)
            return None
        selfie_embedding = np.array(embedding_objs[0]["embedding"])
        os.unlink(tmp_path)
    except:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return None

    # Cosine similarity (higher = more similar)
    similarity = 1 - cosine(stored_embedding, selfie_embedding)
    return similarity

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
            with st.spinner("Processing photos with ArcFace... (first run may take 30s to download model)"):
                embedding = create_embedding_from_photos(uploaded_files)
                if embedding is not None:
                    save_profile(name, embedding, len(uploaded_files))
                    st.success(f"✅ Profile '{name}' created with {len(uploaded_files)} photos!")
                    st.balloons()
                else:
                    st.error("No valid faces found in any photo. Try again with clear, front-facing images.")

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
            with st.spinner("Verifying with ArcFace..."):
                selfie_bytes = selfie.getvalue()
                stored_embedding, meta = load_profile(selected_profile)
                similarity = verify_selfie(selfie_bytes, stored_embedding)
                
                if similarity is None:
                    st.error("❌ No face detected in selfie!")
                else:
                    threshold = 0.65  # ArcFace: 0.6–0.7 is good
                    if similarity > threshold:
                        st.success(f"✅ Welcome, **{selected_profile}**! (Similarity: {similarity:.3f})")
                        st.session_state["logged_in"] = selected_profile
                    else:
                        st.error(f"❌ Face not recognized. Similarity: {similarity:.3f} (threshold: {threshold})")

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
