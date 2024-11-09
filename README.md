# Installation Guide

1. **Create a new virtual environment**:
   - Open a terminal in VSCode.
   - Run the following command to create a virtual environment:
     ```bash
     python -m venv venv
     ```

2. **Activate the virtual environment**:
   - For **Windows**:
     ```bash
     .\venv\Scripts\activate
     ```
   - For **macOS/Linux**:
     ```bash
     source venv/bin/activate
     ```

3. **Install required dependencies**:
   - Once the virtual environment is activated, install the required packages using:
     ```bash
     pip install -r requirements.txt
     ```
4. **Make a new Mysql Database**:
     Make a new database called "eclass"

5. **Run the app**:
   ```bash
     python main.py
   ```

Access the api on [localhost:8000/docs)](http://localhost:8000/docs)
