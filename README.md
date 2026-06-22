# ClarityPC AI Assistant

A Flask-based AI assistant that monitors your PC in real time and explains its health in plain English. It reads live CPU, memory, disk, and process data with `psutil`, and lets you chat with a Llama 3 model (via the Hugging Face Inference API) that answers using your machine's actual current state. A live dashboard visualizes everything with auto-refreshing charts.

## 🚀 Features

- **Real-time monitoring**: Live CPU, memory, disk, and process stats with auto-refreshing charts
- **AI system chat**: Ask about your PC in plain English — answers are grounded in your real-time metrics (Llama 3 via Hugging Face)
- **Automated health analysis**: Rule-based engine flags issues, gives recommendations, and scores overall system health (0–100)
- **Quick actions**: Clean temp files and terminate runaway processes from the dashboard
- **RESTful API**: Clean Flask backend that's easy to integrate or extend

## 🛠️ Technology Stack

- **Backend**: Python, Flask, Flask-CORS
- **AI Integration**: Hugging Face Inference API (Meta Llama 3 8B Instruct)
- **Frontend**: HTML, CSS, JavaScript, Chart.js
- **System Monitoring**: psutil

## 📋 Prerequisites

- Python 3.8 or higher
- A Hugging Face access token — free ([get one here](https://huggingface.co/settings/tokens))
- pip (Python package manager)
- **Platform**: Built and tested on Windows (disk stats target the `C:` drive; adjust `app.py` for macOS/Linux)

## 🔧 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/claritypc_ai.git
   cd claritypc_ai
   ```

2. **Set up virtual environment**
   ```bash
   cd backend
   python -m venv venv
   
   # On Windows:
   venv\Scripts\activate
   
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure your token**
   - Copy `.env.example` to `.env` in the `backend` directory
   - Add your Hugging Face access token:
     ```
     HF_TOKEN=your_token_here
     ```
   - (System monitoring works without a token; only the AI chat requires one.)

## 🚀 Usage

1. **Start the backend server**
   ```bash
   cd backend
   python app.py
   ```
   The server will run on `http://localhost:5000`

2. **Open the frontend**
   - Open `frontend/index.html` in your web browser
   - Or serve it using a local web server:
     ```bash
     # Using Python's built-in server
     cd frontend
     python -m http.server 8000
     ```
     Then navigate to `http://localhost:8000`

3. **Start chatting**
   - Type your PC issue or question in the chat interface
   - Receive AI-powered troubleshooting assistance
   - Follow the step-by-step guidance provided

## 📁 Project Structure

```
claritypc_ai/
├── backend/
│   ├── app.py              # Main Flask application + API endpoints
│   ├── requirements.txt    # Python dependencies
│   ├── .env.example        # Template for your HF_TOKEN (copy to .env)
│   └── venv/               # Virtual environment (not in git)
├── frontend/
│   └── index.html          # Single-page dashboard (Chart.js)
├── .gitignore
└── README.md
```

## 🔒 Security Notes

- **Never commit your `.env` file or access tokens to version control**
- The `.gitignore` file is configured to exclude sensitive files
- Keep your Hugging Face token secure and rotate it if exposed
- The `/processes/kill` and `/actions/cleanup` endpoints modify your system — review before exposing the server beyond localhost

## 🎯 Use Cases

- **PC Troubleshooting**: Diagnose and fix common Windows, macOS, or Linux issues
- **Software Installation**: Get guidance on installing and configuring software
- **Performance Optimization**: Receive tips for improving system performance
- **Error Resolution**: Understand and resolve system error messages
- **Hardware Diagnostics**: Get help identifying hardware-related problems

## 📝 Example Queries

- "My computer is running slow, what should I check?"
- "How do I fix a blue screen error in Windows?"
- "My Wi-Fi keeps disconnecting, help me troubleshoot"
- "How do I check if my hard drive is failing?"
- "What's using all my CPU resources?"

## 🤝 Contributing

Contributions are welcome! If you'd like to improve ClarityPC AI:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is open source and available under the MIT License.

## 👤 Author

**Ameer Omer**
- GitHub: [@ameeromer202-IT](https://github.com/ameeromer202-IT)

## 🙏 Acknowledgments

- Hugging Face for the Inference API and open models
- Meta for the Llama 3 model
- Flask and psutil for the backend infrastructure
- Chart.js for the dashboard visualizations

## 📧 Support

If you have any questions or run into issues, please open an issue on GitHub or contact me directly.

---

**Note**: The AI chat uses the Hugging Face Inference API, which has a free tier. Review Hugging Face's usage limits if you plan to deploy this widely.
