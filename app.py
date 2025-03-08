import streamlit as st
import requests
import os
import tempfile
import subprocess
import speech_recognition as sr
import google.generativeai as genai
from gtts import gTTS
from dotenv import load_dotenv
from radon.complexity import cc_visit
from radon.raw import analyze
import re
import pytest

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

genai.configure(api_key=GOOGLE_API_KEY)

def analyze_code(code):
    if not GOOGLE_API_KEY:
        return "Error: API key not found. Please check .env file."
    
    model = genai.GenerativeModel("gemini-1.5-pro")
    response = model.generate_content(
        f"Review this code and suggest improvements:\n\n{code}\n\nProvide suggestions followed by an improved version of the code."
    )
    return response.text if response else "Error fetching response."

def run_linter(file_path, language):
    try:
        if language == "py":
            result = subprocess.run(["pylint", file_path], capture_output=True, text=True)
        elif language == "js":
            result = subprocess.run(["eslint", file_path], capture_output=True, text=True)
        else:
            return "Linting not supported for this language."
        
        return result.stdout
    except FileNotFoundError:
        return "Linter Error: Linter tool not found. Please install the necessary linter."

def calculate_complexity(code):
    try:
        complexity_results = cc_visit(code)
        complexity_scores = [block.complexity for block in complexity_results]
        return sum(complexity_scores) / len(complexity_scores) if complexity_scores else 0
    except Exception as e:
        return str(e)

def generate_unit_tests(code):
    if not GOOGLE_API_KEY:
        return "Error: API key missing!"
    
    model = genai.GenerativeModel("gemini-1.5-pro")
    response = model.generate_content(
        f"Generate unit tests for this code:\n\n{code}\n\nUse standard unit testing framework."
    )
    return response.text if response else "Error fetching response."

def detect_security_issues(code):
    issues = []
    if re.search(r'(?i)apikey|password|secret|token', code):
        issues.append("Possible hardcoded API key or password detected.")
    if re.search(r'(?i)(SELECT .* FROM .* WHERE .*=[^?])', code):
        issues.append("Potential SQL Injection risk detected.")
    if re.search(r'(?i)(<script>.*</script>)', code):
        issues.append("Possible XSS vulnerability detected.")
    return "\n".join(issues) if issues else "No security issues detected."

def check_test_coverage():
    try:
        result = subprocess.run(["pytest", "--cov"], capture_output=True, text=True)
        if not result.stdout.strip():
            return "No test coverage data found. Ensure you have tests."
        return result.stdout
    except FileNotFoundError:
        return "Pytest or coverage tool not found. Please install pytest-cov."

def optimize_performance(code):
    suggestions = []
    if re.search(r'for .* in range\(.*\):\n\s+for .* in range\(.*\):', code):
        suggestions.append("Nested loops detected. Consider optimizing with vectorization or caching.")
    if re.search(r'\[.*\] for .* in .*', code):
        suggestions.append("List comprehension detected. Ensure it doesn't cause excessive memory usage.")
    return "\n".join(suggestions) if suggestions else "No performance issues detected."

def fetch_github_code(url):
    if url.startswith("https://github.com/"):
        raw_url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob", "")
        response = requests.get(raw_url)
        return response.text if response.status_code == 200 else "Error fetching code."
    return "Invalid GitHub URL."

uploaded_file = st.file_uploader("Upload your code file", type=["py", "js", "java", "cpp", "ts", "go"])
github_url = st.text_input("Or enter a GitHub file URL")
code_input = st.text_area("Or paste your code here")

code_to_analyze = uploaded_file.getvalue().decode("utf-8") if uploaded_file else fetch_github_code(github_url) if github_url else code_input.strip()

if code_to_analyze:
    st.subheader("Code Analysis Results")
    st.write(analyze_code(code_to_analyze))
    
    st.subheader("Linter & Security Checks")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as temp_file:
        temp_file.write(code_to_analyze.encode("utf-8"))
        temp_path = temp_file.name
    st.code(run_linter(temp_path, "py"))
    os.remove(temp_path)
    
    st.subheader("Security & Vulnerability Detection")
    st.write(detect_security_issues(code_to_analyze))
    
    st.subheader("Code Complexity Analysis")
    st.write(f"Cyclomatic Complexity: {calculate_complexity(code_to_analyze):.2f}")
    
    st.subheader("Testing Coverage & Best Practices")
    st.code(check_test_coverage())
    
    st.subheader("Performance Optimization")
    st.write(optimize_performance(code_to_analyze))
    
    st.subheader("GitHub & CI/CD Integration")
    st.write("Ensure this bot runs on PRs, integrates with GitHub Actions, and triggers automated reviews.")
else:
    st.warning("Please upload a file, enter a GitHub URL, or paste your code.")

def recognize_speech():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.write("Speak your question...")
        try:
            audio = recognizer.listen(source)
            return recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            return "Could not understand the audio."
        except sr.RequestError:
            return "Speech recognition service unavailable."

def text_to_speech(text):
    tts = gTTS(text)
    temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
    tts.save(temp_audio)
    return temp_audio

if st.button("Ask a Code Question"):
    question = recognize_speech()
    st.write(f"You asked: {question}")
    answer = analyze_code(question)
    audio_path = text_to_speech(answer)
    
    st.audio(audio_path, format="audio/mp3")
    with open(audio_path, "rb") as file:
        st.download_button(label="Download AI Response (MP3)", data=file, file_name="ai_response.mp3", mime="audio/mp3")
    
    st.write(answer)