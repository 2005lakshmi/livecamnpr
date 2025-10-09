import streamlit as st
import json
import hashlib
from datetime import datetime

# Initialize session state
if 'profiles' not in st.session_state:
    st.session_state.profiles = {}
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'auth_method' not in st.session_state:
    st.session_state.auth_method = None

def get_fingerprint_component():
    """Returns HTML/JS for fingerprint authentication"""
    return """
    <div id="auth-container" style="text-align: center; padding: 20px;">
        <button id="auth-btn" style="padding: 12px 24px; font-size: 16px; background: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer;">
            {button_text}
        </button>
        <div id="auth-status" style="margin-top: 15px; min-height: 24px;"></div>
    </div>

    <script>
    const authBtn = document.getElementById('auth-btn');
    const statusDiv = document.getElementById('auth-status');
    
    authBtn.addEventListener('click', async () => {
        // Check for WebAuthn support
        if (!window.PublicKeyCredential) {
            window.parent.postMessage({type: 'streamlit:setComponentValue', value: {error: 'no_webauthn'}}, '*');
            return;
        }
        
        try {
            statusDiv.innerHTML = '<span style="color: #2196F3;">⏳ Processing...</span>';
            authBtn.disabled = true;
            
            // Generate random challenge
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
            
            // Create credential (registration) or get assertion (login)
            const isRegistration = "{action}" === "register";
            let result;
            
            if (isRegistration) {
                const credential = await navigator.credentials.create({ publicKey });
                result = {
                    success: true,
                    action: "register",
                    credentialId: Array.from(new Uint8Array(credential.rawId)),
                    publicKey: Array.from(new Uint8Array(credential.response.getPublicKey()))
                };
            } else {
                // For login, we'd normally verify against stored credentials
                // Simplified for demo - just verify user presence
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

def get_pin_component(action):
    """Returns HTML/JS for PIN input"""
    return f"""
    <div id="pin-container" style="text-align: center; padding: 20px;">
        <input type="password" id="pin-input" placeholder="Enter 4-digit PIN" maxlength="4" 
               style="padding: 10px; font-size: 18px; width: 120px; text-align: center; margin-bottom: 10px;">
        <br>
        <button id="pin-btn" style="padding: 10px 20px; font-size: 16px; background: #2196F3; color: white; border: none; border-radius: 4px;">
            {action}
        </button>
        <div id="pin-status" style="margin-top: 15px; min-height: 24px;"></div>
    </div>

    <script>
    const pinInput = document.getElementById('pin-input');
    const pinBtn = document.getElementById('pin-btn');
    const pinStatus = document.getElementById('pin-status');
    
    pinBtn.addEventListener('click', () => {{
        const pin = pinInput.value;
        if (!/^\d{{4}}$/.test(pin)) {{
            pinStatus.innerHTML = '<span style="color: #f44336;">Please enter a 4-digit PIN</span>';
            return;
        }}
        
        window.parent.postMessage({{
            type: 'streamlit:setComponentValue',
            value: {{pin: pin, action: "{action.lower()}"}}
        }}, '*');
        pinStatus.innerHTML = '<span style="color: #4CAF50;">Processing...</span>';
    }});
    
    pinInput.addEventListener('keypress', (e) => {{
        if (e.key === 'Enter') pinBtn.click();
    }});
    </script>
    """

def create_profile(username, auth_data, method):
    """Create new user profile"""
    st.session_state.profiles[username] = {
        'method': method,
        'created': datetime.now().isoformat(),
        'auth_data': auth_data
    }
    st.session_state.current_user = username
    st.session_state.auth_method = method

def verify_pin(username, pin):
    """Verify PIN for existing user"""
    if username in st.session_state.profiles:
        stored_pin = st.session_state.profiles[username].get('pin')
        return stored_pin == pin
    return False

def main():
    st.set_page_config(page_title="Biometric Profile Auth", layout="centered")
    st.title("🔐 Biometric Profile Authentication")
    
    # Check device capabilities
    device_support = st.radio(
        "Select your device type:",
        ["📱 Smartphone/Tablet (with fingerprint)", "💻 Computer (without fingerprint)"],
        key="device_type"
    )
    
    has_fingerprint = device_support.startswith("📱")
    
    if st.session_state.current_user:
        # User is logged in
        st.success(f"Welcome back, **{st.session_state.current_user}**!")
        st.write(f"Authenticated using: **{st.session_state.auth_method}**")
        
        if st.button("🚪 Logout"):
            st.session_state.current_user = None
            st.session_state.auth_method = None
            st.rerun()
            
    else:
        # Authentication flow
        tab1, tab2 = st.tabs(["🆕 Create Profile", "🚪 Login"])
        
        with tab1:
            st.subheader("Create New Profile")
            new_username = st.text_input("Choose a username", key="new_user")
            
            if new_username:
                if new_username in st.session_state.profiles:
                    st.error("Username already exists! Please choose another.")
                else:
                    if has_fingerprint:
                        st.info("Touch your fingerprint sensor to register")
                        component_html = get_fingerprint_component().format(
                            button_text="Register with Fingerprint", 
                            action="register"
                        )
                        auth_result = st.components.v1.html(component_html, height=150)
                        
                        # Handle registration result
                        if auth_result and isinstance(auth_result, dict):
                            if 'error' in auth_result:
                                if auth_result['error'] == 'no_webauthn':
                                    st.warning("Fingerprint not supported. Please use PIN method.")
                                else:
                                    st.error(f"Registration failed: {auth_result['error']}")
                            elif auth_result.get('success'):
                                # Store minimal auth data (in real app, store credential ID)
                                create_profile(new_username, {"registered": True}, "Fingerprint")
                                st.success("Profile created successfully!")
                                st.rerun()
                    else:
                        st.info("Create a 4-digit PIN for your profile")
                        component_html = get_pin_component("Create PIN")
                        pin_result = st.components.v1.html(component_html, height=150)
                        
                        if pin_result and isinstance(pin_result, dict):
                            if 'pin' in pin_result:
                                # Store PIN (in real app, hash it!)
                                st.session_state.profiles[new_username] = {
                                    'method': 'PIN',
                                    'pin': pin_result['pin'],
                                    'created': datetime.now().isoformat()
                                }
                                st.session_state.current_user = new_username
                                st.session_state.auth_method = 'PIN'
                                st.success("Profile created with PIN!")
                                st.rerun()
        
        with tab2:
            st.subheader("Login to Existing Profile")
            existing_user = st.selectbox(
                "Select your username", 
                options=list(st.session_state.profiles.keys()),
                key="existing_user"
            )
            
            if existing_user:
                user_method = st.session_state.profiles[existing_user]['method']
                
                if has_fingerprint and user_method == "Fingerprint":
                    st.info("Verify your fingerprint to login")
                    component_html = get_fingerprint_component().format(
                        button_text="Login with Fingerprint", 
                        action="login"
                    )
                    auth_result = st.components.v1.html(component_html, height=150)
                    
                    if auth_result and isinstance(auth_result, dict):
                        if 'error' in auth_result:
                            st.error(f"Login failed: {auth_result['error']}")
                        elif auth_result.get('success'):
                            st.session_state.current_user = existing_user
                            st.session_state.auth_method = "Fingerprint"
                            st.success("Login successful!")
                            st.rerun()
                
                elif not has_fingerprint or user_method == "PIN":
                    st.info("Enter your PIN to login")
                    component_html = get_pin_component("Login with PIN")
                    pin_result = st.components.v1.html(component_html, height=150)
                    
                    if pin_result and isinstance(pin_result, dict):
                        if 'pin' in pin_result:
                            if verify_pin(existing_user, pin_result['pin']):
                                st.session_state.current_user = existing_user
                                st.session_state.auth_method = "PIN"
                                st.success("Login successful!")
                                st.rerun()
                            else:
                                st.error("Invalid PIN!")

if __name__ == "__main__":
    main()
