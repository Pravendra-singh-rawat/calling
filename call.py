import streamlit as st
import pandas as pd
import tempfile
import os
import whisper

# --- 1. Load Whisper Model (Run once) ---
# We load the 'base' model for decent speed and accuracy.
# This will download the model weights the first time it's run.
@st.cache_resource
def load_whisper_model():
    """Loads the Whisper model into memory."""
    try:
        model = whisper.load_model("base")
        return model
    except Exception as e:
        st.error(f"Could not load Whisper model. Ensure you have ffmpeg installed and enough memory. Error: {e}")
        return None

# --- 2. Transcription Function ---
def transcribe_audio_file(model, audio_path):
    """Transcribes an audio file using the loaded Whisper model."""
    try:
        # Use a context manager to ensure memory is handled correctly
        result = model.transcribe(audio_path, fp16=False) # fp16=False recommended for CPU
        return result["text"]
    except Exception as e:
        st.error(f"Transcription failed for {audio_path}: {e}")
        return "ERROR: Failed to transcribe."

# --- 3. LLM/Analysis Simulation Function ---
def analyze_transcript_for_exam_duty(transcript):
    """
    Simulates the LLM analysis for the 'Exam Duty' conclusion.
    
    In a real app, this would be an API call to GPT-4, Gemini, etc., 
    with a complex prompt. Here, we use simple keyword matching for demo purposes.
    """
    transcript_lower = transcript.lower()
    
    # Check for acceptance keywords
    if any(keyword in transcript_lower for keyword in ["yes, i can", "i'll do it", "i accept", "sure, i will"]):
        conclusion = "Accepted"
        reason = "Agreed to take on the duty."
    
    # Check for decline/unclear keywords
    elif any(keyword in transcript_lower for keyword in ["i can't", "not possible", "already booked", "i'm busy"]):
        conclusion = "Declined"
        
        # Simple rule to extract a reason
        if "already booked" in transcript_lower:
            reason = "Declined, citing prior booking."
        elif "not possible" in transcript_lower:
            reason = "Declined, stating it's not possible."
        else:
            reason = "Declined (Reason unclear from keywords)."
            
    # Default to pending/unclear
    else:
        conclusion = "Unclear/Pending"
        reason = "The final decision was not clearly stated."
        
    return conclusion, reason

# --- 4. Streamlit App Layout ---
def main():
    st.title("🎤 Bulk Audio Transcription & Exam Duty Analysis")
    st.markdown("Upload multiple audio files for automated transcription and conclusion extraction.")
    
    # Load model once
    whisper_model = load_whisper_model()
    if not whisper_model:
        return # Stop execution if model failed to load

    # Bulk file uploader
    uploaded_files = st.file_uploader(
        "Upload multiple voice recordings (.mp3, .wav)",
        type=['mp3', 'wav'],
        accept_multiple_files=True
    )
    
    results_list = []
    
    if uploaded_files and st.button("Start Bulk Analysis"):
        st.info(f"Processing {len(uploaded_files)} files. This will take some time...")
        
        # Use a Streamlit progress bar
        progress_bar = st.progress(0)
        
        # Create a temporary directory for file processing
        with tempfile.TemporaryDirectory() as temp_dir:
            
            for i, uploaded_file in enumerate(uploaded_files):
                file_name = uploaded_file.name
                st.write(f"**Processing:** {file_name}")
                
                # 1. Save the uploaded file to the temporary directory
                temp_audio_path = os.path.join(temp_dir, file_name)
                with open(temp_audio_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                # 2. Transcribe the audio
                full_transcript = transcribe_audio_file(whisper_model, temp_audio_path)
                
                # 3. Analyze the transcript
                conclusion, reason = analyze_transcript_for_exam_duty(full_transcript)
                
                # 4. Store results
                results_list.append({
                    "File Name": file_name,
                    "Conclusion": conclusion,
                    "Reason/Condition": reason,
                    "Transcript Snippet": full_transcript[:100] + "..." if len(full_transcript) > 100 else full_transcript
                })

                # Update progress bar
                progress_bar.progress((i + 1) / len(uploaded_files))

        st.success("Analysis Complete!")
        
        # 5. Display the results table
        st.subheader("✅ Bulk Analysis Results Table")
        df_results = pd.DataFrame(results_list)
        
        # Display the interactive table
        st.dataframe(df_results, use_container_width=True)
        
        # Provide option to download
        csv = df_results.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Results as CSV",
            data=csv,
            file_name='audio_analysis_results.csv',
            mime='text/csv',
        )


if __name__ == "__main__":
    main()
