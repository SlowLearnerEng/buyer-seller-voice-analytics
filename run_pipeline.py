import subprocess
import time
import os
import sys

def run_step(command, step_name):
    print(f"\n🚀 Starting Step: {step_name}...")
    try:
        # Check if python command
        cmd_list = command.split()
        if cmd_list[0] == "python":
            subprocess.check_call([sys.executable] + cmd_list[1:])
        elif cmd_list[0] == "streamlit":
             # Streamlit usually blocks, so we might want to just run it as final step or Popen
             # For a pipeline script, usually we want to Prepare data then Open UI
             subprocess.run(cmd_list, check=True)
        else:
            subprocess.check_call(cmd_list)
        print(f"✅ Step '{step_name}' completed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Step '{step_name}' failed with error: {e}")
        return False

def main():
    print("==================================================")
    print("   🎙️ Buyer-Seller Voice Analytics Pipeline      ")
    print("==================================================")
    
    # Check Prereqs
    if not os.path.exists("Input.csv"):
        print("❌ Error: 'Input.csv' not found. Please place your raw data CSV in this directory.")
        return

    # STEP 1: Analyze Transcriptions (Input.csv -> output_TIMESTAMP.csv)
    # Note: analyze_transcriptions.py reads Input.csv by default unless modified
    if not run_step("python analyze_transcriptions.py", "Analyze Transcriptions (LLM)"):
        return

    # STEP 2: Generate Insights (output_TIMESTAMP.csv -> *_level.csv)
    # generate_insights.py automatically finds the latest output_*.csv
    if not run_step("python generate_insights.py", "Generate Insights & Metrics"):
        return
        
    # NOTE Check
    if not os.path.exists("Products-mapping - matched_by_llm.csv"):
        print("\n⚠️  WARNING: 'Products-mapping - matched_by_llm.csv' not found.")
        print("   The 'Price Opportunities' dashboard requires this file.")
        print("   Ensure you generate it or place it in the directory manually.")
    
    print("\n✅ Data Pipeline Completed!")
    print("   You can now run the dashboard:")
    print("   > streamlit run app.py")
    
    # Optional: Launch Dashboard
    choice = input("\nDo you want to launch the dashboard now? (y/n): ").lower()
    if choice == 'y':
        run_step("streamlit run app.py", "Launch Dashboard")

if __name__ == "__main__":
    main()
