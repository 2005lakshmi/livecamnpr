import streamlit as st
import cv2
import numpy as np

# Function to capture and display live video feed
def live_stream():
    # Open the webcam (0 for default camera)
    import cv2

    #url = "https://192.168.171.178:8080/video"
    cap = cv2.VideoCapture(0)

    # Check if the webcam opened correctly
    if not cap.isOpened():
        st.error("Error: Could not access the camera.")
        return

    # Streamlit header
    st.page_link("https://www.circuitdigest.cloud/",label="create an api here")
    st.title(":blue[LIVE]")

    # Display a placeholder to hold the video feed
    placeholder = st.empty()

    # Create a checkbox for capturing the image
    #capture_checkbox = st.checkbox("Capture Screenshot", key="capture_ss_checkbox")

    # Initialize the variable for the captured image
    captured_image = None

    # Display a button to start and stop the streaming if needed
    capture_button = st.button("Capture Image")
    i = 0
    # Main loop to capture frames
    while True:
        # Read the frame from the webcam
        ret, frame = cap.read()

        # If frame is not read correctly, stop the stream
        if not ret:
            st.error("Error: Failed to capture frame.")
            break

        # Convert the frame to RGB (OpenCV uses BGR, but Streamlit uses RGB)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Display the current frame in Streamlit using the placeholder
        placeholder.image(frame_rgb, channels="RGB", use_column_width=True)

        # Capture an image when the checkbox or button is pressed
        if capture_button:
            captured_image = frame_rgb


            import os
            save_directory = "captured_images"
            if not os.path.exists(save_directory):
                os.makedirs(save_directory)
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_path = os.path.join(save_directory, f"captured_{timestamp}.jpg")

            # Save the image to the specified path
            cv2.imwrite(image_path, cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR))  # Convert RGB back to BGR for saving


            st.image(captured_image, caption="Captured Image", use_column_width=True)
            #st.write(f"lnj--{i}")
            i = i+1
            #captured_image = None
            #capture_button = None



            
            import requests 
            import os
            #image_path = os.path.abspath(captured_image)
            #api_key = input("Enter your API key: ")
            api_key = "HQsIpTsdCUux"

            # API details
            url = "https://www.circuitdigest.cloud/readnumberplate"  # API endpoint

            # Read the image file in binary mode
            with open(image_path, "rb") as image_file:
                # Prepare the payload
                files = {
                    "imageFile": (f"{api_key}.jpg", image_file, "image/jpg")
                }
                headers = {
                    "Authorization": api_key  # Use the API key provided by the user
                }

                # Send the request
                try:
                    response = requests.post(url, headers=headers, files=files)

                    # Check if request was successful
                    if response.status_code == 200:
                        st.success("Request successful!")
                        # Parse JSON response
                        response_data = response.json()
                        #print(response_data)

                        # Extract number plate data and image link
                        number_plate = response_data.get("data", {}).get("number_plate", "Not found")
                        image_link = response_data.get("data", {}).get("view_image", "")

                        st.write("Number Plate:", number_plate)

                        # Ensure the image link has the correct scheme
                        if not image_link.startswith("http"):
                            image_link = "https://" + image_link

                        # Display the image link as a clickable URL
                        if image_link:
                            #print(f"Click the link to view the image: {image_link}")
                            import cv2
                            import numpy as np
                            import requests

                            # URL of the image
                            url = "https://www.circuitdigest.cloud/static/HQsIpTsdCUux.jpg"

                            # Send an HTTP GET request to the image URL
                            response = requests.get(url)

                            # Check if the request was successful
                            if response.status_code == 200:
                                # Convert the image to a NumPy array
                                image_array = np.asarray(bytearray(response.content), dtype=np.uint8)

                                # Decode the array into an OpenCV image
                                img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
                                
                                if img is not None:
                                    # Display the image using OpenCV
                                    #cv2.imshow("Downloaded Image", img)

                                    # Wait for a key press and close the window
                                    cv2.waitKey(0)
                                    cv2.destroyAllWindows()
                                else:
                                    st.error("Failed to decode the image.")
                            else:
                                st.error(f"Failed to download the image. Status code: {response.status_code}")
                        else:
                            st.error("No image link available.")
                    else:
                        st.error(f"Request failed with status code {response.status_code}")
                        st.error("Response:", response.text)

                except requests.exceptions.RequestException as e:
                    st.error(f"Error connecting to the API:{e}")

            captured_image = None
            capture_button = None






























        # Display the captured image below the stream (if any)
        
    # Release the camera and close all OpenCV windows
    cap.release()

# Run the live stream function
if __name__ == "__main__":
    live_stream()
