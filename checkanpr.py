import streamlit as st
import base64
from datetime import datetime

# Initialize session state
if 'profiles' not in st.session_state:
    st.session_state.profiles = {}
if 'current_user' not in st.session_state:
    st.session_state.current_user = None

def get_fingerprint_component():
    return """
    <div id="auth-container" style="text-align: center; padding: 20px;">
        <button id="auth-btn" style="padding: 12px 24px; font-size: 16px; background: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer;">
            BUTTON_TEXT_PLACEHOLDER
        </button>
        <div id="auth-status" style="margin-top: 15px; min-height: 24px;"></div>
    </div>

    <script>
    const authBtn = document.getElementById('auth-btn');
    const statusDiv = document.getElementById('auth-status');
    
    authBtn.addEventListener('click', async () => {
        if (!window.PublicKeyCredential) {
            window.parent.postMessage({type: 'streamlit:setComponentValue', value: {error: 'no_webauthn'}}, '*');
            return;
        }
        
        try {
            statusDiv.innerHTML = '<span style="color: #2196F3;">⏳ Processing...</span>';
            authBtn.disabled = true;
            
            const challenge = new Uint8Array(32);
            window.crypto.getRandomValues(challenge);
            
            const ACTION = "ACTION_PLACEHOLDER";
            let result;
            
            if (ACTION === "register") {
                const publicKey = {
                    challenge: challenge,
                    rp: { name: "ProfileAuth" },
                    user: {
                        id: new TextEncoder().encode("user_" + Date.now()),
                        name: "user@example.com",
                        displayName: "User"
                    },
                    pubKeyCredParams: [{ alg: -7, type: "public-key" }],
                    timeout: 60000,
                    authenticatorSelection: {
                        authenticatorAttachment: "platform",
                        userVerification: "required"
                    }
                };
                
                const credential = await navigator.credentials.create({ publicKey });
                const credentialId = Array.from(new Uint8Array(credential.rawId));
                
                result = {
                    success: true,
                    action: "register",
                    credentialId: credentialId
                };
            } else if (ACTION === "login") {
                // Get allowed credential IDs from Python
                const allowedCreds = CREDENTIALS_PLACEHOLDER;
                const allowCredentials = allowedCreds.map(id => ({
                    id: new Uint8Array(id).buffer,
                    type: "public-key"
                }));
                
                const publicKey = {
                    challenge: challenge,
                    timeout: 60000,
                    userVerification: "required",
                    allowCredentials: allowCredentials
                };
                
                const assertion = await navigator.credentials.get({ publicKey });
                result = {
                    success: true,
                    action: "login"
                };
            }
            
            window.parent.postMessage({type: 'streamlit:setComponentValue', value: result}, '*');
            statusDiv.innerHTML = '<span style="color: #4CAF50;">✅ Success!</span>';
            
        } catch (error) {
            console.error("Auth error:", error);
            let errorMsg = error.name || "Authentication failed";
            if (errorMsg === "NotAllowedError") errorMsg = "Operation cancelled";
            
            window.parent.postMessage({
                type: 'streamlit:setComponentValue', 
                value: {error: errorMsg}
            }, '*');
            statusDiv.innerHTML = `<span style="color: #f44336;">❌ ${errorMsg}</span>`;
        } finally {
            authBtn.disabled = false;
        }
    });
    </script>
    """

def get_pin_component():
    return """
    <div id="pin-container" style="text-align: center; padding: 20px;">
        <input type="password" id="pin-input" placeholder="Enter 4-digit PIN" maxlength="4" 
               style="padding: 10px; font-size: 18px; width: 120px; text-align: center; margin-bottom: 10px;">
        <br>
        <button id="pin-btn" style="padding: 10px 20px; font-size: 16px; background: #2196F3; color: white; border: none; border-radius: 4px;">
            ACTION_PLACEHOLDER
        </button>
        <div id="pin-status" style="margin-top: 15px; min-height: 24px;"></div>
    </div>

    <script>
    const pinInput = document.getElementById('pin-input');
    const pinBtn = document.getElementById('pin-btn');
    const pinStatus = document.getElementById('pin-status');
    
    pinBtn.addEventListener('click', () => {
        const pin = pinInput.value;
        if (!/^\\d{4}$/.test(pin)) {
            pinStatus.innerHTML = '<span style="color: #f44336;">Please enter a 4-digit PIN</span>';
            return;
        }
        
        const actionType = "ACTION_TYPE_PLACEHOLDER";
        window.parent.postMessage({
            type: 'streamlit:setComponentValue',
            value: {pin: pin, action: actionType}
        }, '*');
        pinStatus.innerHTML = '<span style="color: #4CAF50;">Processing...</span>';
    });
    
    pinInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') pinBtn.click();
    });
    </script>
    """

def create_profile(username, method, credential_id=None, pin=None):
    profile_data = {
        'method': method,
        'created': datetime.now().isoformat()
    }
    if credential_id:
        # Store as base64 for safe JSON serialization
        profile_data['credential_id'] = base64.b64encode(bytes(credential_id)).decode('utf-8')
    if pin:
        profile_data['pin'] = pin  # In production: hash this!
    
    st.session_state.profiles[username] = profile_data

def get_credential_id(username):
    """Get decoded credential ID for a user"""
    cred_b64 = st.session_state.profiles[username].get('credential_id')
    if cred_b64:
        return list(base64.b64decode(cred_b64))
    return None

def verify_pin(username, pin):
    if username in st.session_state.profiles:
        return st.session_state.profiles[username].get('pin') == pin
    return False

def main():
    st.set_page_config(page_title="Profile-Specific Fingerprint Auth", layout="centered")
    st.title("🔐 Profile-Specific Biometric Auth")
    
    device_support = st.radio(
        "Select your device:",
        ["📱 Smartphone/Tablet (with fingerprint)", "💻 Computer (without fingerprint)"],
        key="device_type"
    )
    
    has_fingerprint = device_support.startswith("📱")
    
    if st.session_state.current_user:
        st.success(f"✅ Welcome, **{st.session_state.current_user}**!")
        st.write(f"Authenticated via: **{st.session_state.profiles[st.session_state.current_user]['method']}**")
        
        if st.button("🚪 Logout"):
            st.session_state.current_user = None
            st.rerun()
    else:
        tab1, tab2 = st.tabs(["🆕 Create Profile", "🚪 Login"])
        
        with tab1:
            st.subheader("Create New Profile")
            new_username = st.text_input("Choose a username", key="new_user")
            
            if new_username:
                if new_username in st.session_state.profiles:
                    st.error("Username already exists!")
                else:
                    if has_fingerprint:
                        st.info("Register your fingerprint for this profile")
                        html_code = get_fingerprint_component()
                        html_code = html_code.replace("BUTTON_TEXT_PLACEHOLDER", "Register Fingerprint")
                        html_code = html_code.replace("ACTION_PLACEHOLDER", "register")
                        result = st.components.v1.html(html_code, height=150)
                        
                        if result and isinstance(result, dict):
                            if result.get('success') and 'credentialId' in result:
                                create_profile(new_username, "Fingerprint", result['credentialId'])
                                st.success("✅ Profile created! Fingerprint registered.")
                                st.rerun()
                            elif 'error' in result:
                                st.error(f"Registration failed: {result['error']}")
                    else:
                        st.info("Create a 4-digit PIN for this profile")
                        html_code = get_pin_component()
                        html_code = html_code.replace("ACTION_PLACEHOLDER", "Create PIN")
                        html_code = html_code.replace("ACTION_TYPE_PLACEHOLDER", "create")
                        result = st.components.v1.html(html_code, height=150)
                        
                        if result and isinstance(result, dict):
                            if 'pin' in result and result.get('action') == 'create':
                                create_profile(new_username, "PIN", pin=result['pin'])
                                st.success("✅ Profile created with PIN!")
                                st.rerun()
        
        with tab2:
            st.subheader("Login to Existing Profile")
            if not st.session_state.profiles:
                st.info("No profiles exist. Create one first!")
            else:
                existing_user = st.selectbox(
                    "Select your profile", 
                    options=list(st.session_state.profiles.keys()),
                    key="existing_user"
                )
                
                if existing_user:
                    user_method = st.session_state.profiles[existing_user]['method']
                    
                    if has_fingerprint and user_method == "Fingerprint":
                        st.info(f"Authenticate with the fingerprint registered for **{existing_user}**")
                        # Get credential ID for this profile
                        cred_id = get_credential_id(existing_user)
                        if cred_id:
                            html_code = get_fingerprint_component()
                            html_code = html_code.replace("BUTTON_TEXT_PLACEHOLDER", "Login with Fingerprint")
                            html_code = html_code.replace("ACTION_PLACEHOLDER", "login")
                            # Inject allowed credentials as JS array
                            creds_js = f"const CREDENTIALS_PLACEHOLDER = [{cred_id}];"
                            html_code = creds_js + html_code
                            result = st.components.v1.html(html_code, height=180)
                            
                            if result and isinstance(result, dict):
                                if result.get('success'):
                                    st.session_state.current_user = existing_user
                                    st.success("✅ Login successful!")
                                    st.rerun()
                                elif 'error' in result:
                                    st.error(f"Login failed: {result['error']}")
                        else:
                            st.error("No fingerprint registered for this profile!")
                    
                    else:
                        st.info(f"Enter PIN for **{existing_user}**")
                        html_code = get_pin_component()
                        html_code = html_code.replace("ACTION_PLACEHOLDER", "Login with PIN")
                        html_code = html_code.replace("ACTION_TYPE_PLACEHOLDER", "login")
                        result = st.components.v1.html(html_code, height=150)
                        
                        if result and isinstance(result, dict):
                            if 'pin' in result and result.get('action') == 'login':
                                if verify_pin(existing_user, result['pin']):
                                    st.session_state.current_user = existing_user
                                    st.success("✅ Login successful!")
                                    st.rerun()
                                else:
                                    st.error("❌ Invalid PIN!")

if __name__ == "__main__":
    main()
