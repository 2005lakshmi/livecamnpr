import streamlit as st
from datetime import datetime

# Initialize session state
if 'profiles' not in st.session_state:
    st.session_state.profiles = {}
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'auth_method' not in st.session_state:
    st.session_state.auth_method = None

def get_fingerprint_component():
    """Returns HTML/JS for fingerprint authentication - NO .format() used"""
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
            
            const isRegistration = "ACTION_PLACEHOLDER" === "register";
            let result;
            
            if (isRegistration) {
                const credential = await navigator.credentials.create({ publicKey });
                result = {
                    success: true,
                    action: "register"
                };
            } else {
                const assertion = await navigator.credentials.get({ 
                    publicKey: {
                        challenge: challenge,
                        timeout: 60000,
                        userVerification: "required"
                    }
                });
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
    """Returns HTML/JS for PIN input - NO .format() used"""
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

def create_profile(username, method, pin=None):
    """Create new user profile"""
    profile_data = {
        'method': method,
        'created': datetime.now().isoformat()
    }
    if pin:
        # In production: hash the PIN! (for demo, store as-is in session)
        profile_data['pin'] = pin
    
    st.session_state.profiles[username] = profile_data
    st.session_state.current_user = username
    st.session_state.auth_method = method

def verify_pin(username, pin):
    """Verify PIN for existing user"""
    if username in st.session_state.profiles:
        return st.session_state.profiles[username].get('pin') == pin
    return False

def main():
    st.set_page_config(page_title="Biometric Profile Auth", layout="centered")
    st.title("🔐 Biometric Profile Authentication")
    
    # Device selection
    device_support = st.radio(
        "Select your device:",
        ["📱 Smartphone/Tablet (with fingerprint)", "💻 Computer (without fingerprint)"],
        key="device_type"
    )
    
    has_fingerprint = device_support.startswith("📱")
    
    if st.session_state.current_user:
        st.success(f"✅ Welcome, **{st.session_state.current_user}**!")
        st.write(f"Authenticated via: **{st.session_state.auth_method}**")
        
        if st.button("🚪 Logout"):
            st.session_state.current_user = None
            st.session_state.auth_method = None
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
                        st.info("Touch your fingerprint sensor to register")
                        html_code = get_fingerprint_component()
                        html_code = html_code.replace("BUTTON_TEXT_PLACEHOLDER", "Register with Fingerprint")
                        html_code = html_code.replace("ACTION_PLACEHOLDER", "register")
                        result = st.components.v1.html(html_code, height=150)
                        
                        if result and isinstance(result, dict):
                            if result.get('success'):
                                create_profile(new_username, "Fingerprint")
                                st.success("Profile created!")
                                st.rerun()
                            elif 'error' in result:
                                if result['error'] == 'no_webauthn':
                                    st.warning("Fingerprint not supported. Use a computer to create a PIN profile.")
                                else:
                                    st.error(f"Error: {result['error']}")
                    else:
                        st.info("Create a 4-digit PIN")
                        html_code = get_pin_component()
                        html_code = html_code.replace("ACTION_PLACEHOLDER", "Create PIN")
                        html_code = html_code.replace("ACTION_TYPE_PLACEHOLDER", "create")
                        result = st.components.v1.html(html_code, height=150)
                        
                        if result and isinstance(result, dict):
                            if 'pin' in result and result.get('action') == 'create':
                                create_profile(new_username, "PIN", result['pin'])
                                st.success("Profile created with PIN!")
                                st.rerun()
        
        with tab2:
            st.subheader("Login to Existing Profile")
            if not st.session_state.profiles:
                st.info("No profiles exist. Create one first!")
            else:
                existing_user = st.selectbox(
                    "Select your username", 
                    options=list(st.session_state.profiles.keys()),
                    key="existing_user"
                )
                
                if existing_user:
                    user_method = st.session_state.profiles[existing_user]['method']
                    
                    if has_fingerprint and user_method == "Fingerprint":
                        st.info("Verify your fingerprint")
                        html_code = get_fingerprint_component()
                        html_code = html_code.replace("BUTTON_TEXT_PLACEHOLDER", "Login with Fingerprint")
                        html_code = html_code.replace("ACTION_PLACEHOLDER", "login")
                        result = st.components.v1.html(html_code, height=150)
                        
                        if result and isinstance(result, dict):
                            if result.get('success'):
                                st.session_state.current_user = existing_user
                                st.session_state.auth_method = "Fingerprint"
                                st.success("Login successful!")
                                st.rerun()
                            elif 'error' in result:
                                st.error(f"Login failed: {result['error']}")
                    
                    else:
                        st.info("Enter your PIN")
                        html_code = get_pin_component()
                        html_code = html_code.replace("ACTION_PLACEHOLDER", "Login with PIN")
                        html_code = html_code.replace("ACTION_TYPE_PLACEHOLDER", "login")
                        result = st.components.v1.html(html_code, height=150)
                        
                        if result and isinstance(result, dict):
                            if 'pin' in result and result.get('action') == 'login':
                                if verify_pin(existing_user, result['pin']):
                                    st.session_state.current_user = existing_user
                                    st.session_state.auth_method = "PIN"
                                    st.success("Login successful!")
                                    st.rerun()
                                else:
                                    st.error("Invalid PIN!")

if __name__ == "__main__":
    main()
