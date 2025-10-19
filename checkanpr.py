
from deepface import DeepFace
import tempfile
import os
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


def create_embedding_from_photos(uploaded_files):
    embeddings = []
    for uploaded_file in uploaded_files:
        try:
            # Save to temp file (DeepFace needs file path)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name

            # Extract embedding using Facenet (or VGG-Face)
            embedding_objs = DeepFace.represent(
                img_path=tmp_path,
                model_name="Facenet",  # or "VGG-Face"
                enforce_detection=True
            )
            if embedding_objs:
                embeddings.append(embedding_objs[0]["embedding"])
            else:
                st.warning(f"No face detected in {uploaded_file.name}")
            os.unlink(tmp_path)  # Clean up
        except Exception as e:
            st.error(f"Error processing {uploaded_file.name}: {str(e)}")
    
    if not embeddings:
        return None
    return np.mean(embeddings, axis=0)

def verify_face(selfie_bytes, stored_embedding):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        tmp.write(selfie_bytes)
        tmp_path = tmp.name

    try:
        selfie_embedding = DeepFace.represent(
            img_path=tmp_path,
            model_name="Facenet",
            enforce_detection=True
        )[0]["embedding"]
        os.unlink(tmp_path)
    except:
        os.unlink(tmp_path)
        return None

    # Cosine similarity (DeepFace uses this by default)
    from scipy.spatial.distance import cosine
    similarity = 1 - cosine(stored_embedding, selfie_embedding)
    return similarity  # Higher = more similar (0 to 1)
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
        
        # In Tab 2
        if selfie and st.button("🔓 Verify Login"):
            with st.spinner("Verifying..."):
                selfie_bytes = selfie.getvalue()
                stored_embedding, meta = load_profile(selected_profile)
                similarity = verify_face(selfie_bytes, stored_embedding)
                
                if similarity is None:
                    st.error("❌ No face detected in selfie!")
                else:
                    threshold = 0.7  # Adjust based on model (Facenet: 0.7 is good)
                    if similarity > threshold:
                        st.success(f"✅ Welcome, **{selected_profile}**! (Similarity: {similarity:.2f})")
                        st.session_state["logged_in"] = selected_profile
                    else:
                        st.error(f"❌ Face not recognized. Similarity: {similarity:.2f} (threshold: {threshold})")
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
