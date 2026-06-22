from flask import Flask, jsonify, request
from flask_cors import CORS
import psutil
import platform
import os
import sys
from openai import OpenAI
import threading
import webbrowser
import time

# Make stdout UTF-8 so the emoji status banner doesn't crash on a cp1252 console (Windows)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

app = Flask(__name__)
CORS(app)

def _load_dotenv():
    """Minimal .env loader (no external dependency). Lines like KEY=value."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

_load_dotenv()

# Initialize the AI client.
# This points at an Ollama server (OpenAI-compatible API). Defaults to a local
# Ollama install; override OLLAMA_BASE_URL / OLLAMA_MODEL in a .env file or your
# shell to use a different host or model (see .env.example).
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
# Ollama ignores the API key, but the SDK requires a non-empty string.
client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
print(f"🧠 AI model: {OLLAMA_MODEL} via {OLLAMA_BASE_URL}")

# AI Chat Module
class AIChat:
    """Handles AI chat with context about system state"""
    
    @staticmethod
    def get_system_context(stats, processes):
        """Generate context string for LLM"""
        context = f"""Current System State:
- CPU Usage: {stats['cpu']['usage_percent']}% ({stats['cpu']['core_count']} cores)
- Memory: {stats['memory']['used_gb']}GB / {stats['memory']['total_gb']}GB ({stats['memory']['percent_used']}% used)
- Disk: {stats['disk']['used_gb']}GB / {stats['disk']['total_gb']}GB ({stats['disk']['percent_used']}% used)

Top CPU Processes:"""
        
        for proc in processes['top_cpu'][:5]:
            context += f"\n- {proc['name']}: {proc['cpu_percent']}% CPU, {proc['memory_percent']}% Memory (PID: {proc['pid']})"
        
        context += "\n\nTop Memory Processes:"
        for proc in processes['top_memory'][:5]:
            context += f"\n- {proc['name']}: {proc['memory_percent']}% Memory, {proc['cpu_percent']}% CPU (PID: {proc['pid']})"
        
        return context
    
    @staticmethod
    def chat(user_message, stats, processes):
        """Send message to LLM with system context"""
        try:
            system_context = AIChat.get_system_context(stats, processes)
            
            full_prompt = f"""You are an AI assistant for ClarityPC.AI, a system monitoring tool. 
You help users understand their PC's performance and provide actionable advice.
Be concise, friendly, and technical when needed. Focus on practical solutions.

{system_context}

User Question: {user_message}

Answer the user's question based on this real-time data. If they ask about performance issues, 
reference specific processes and metrics. Keep responses under 150 words unless more detail is needed."""
            
            response = client.chat.completions.create(
                model=OLLAMA_MODEL,
                messages=[{"role": "user", "content": full_prompt}],
                max_tokens=500
            )
            
            return {
                "success": True,
                "message": response.choices[0].message.content
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error communicating with AI: {str(e)}"
            }

# AI Analysis Module
class SystemAnalyzer:
    """Analyzes system data and provides human-readable insights"""
    
    @staticmethod
    def analyze_system(stats, processes):
        """Generate AI-like analysis of system state"""
        issues = []
        recommendations = []
        status = "healthy"
        
        cpu = stats['cpu']['usage_percent']
        mem = stats['memory']['percent_used']
        disk = stats['disk']['percent_used']
        
        # CPU Analysis
        if cpu > 90:
            status = "critical"
            issues.append(f"🔴 CPU is severely overloaded at {cpu}%")
            top_cpu = processes['top_cpu'][0] if processes['top_cpu'] else None
            if top_cpu:
                recommendations.append(f"Consider closing '{top_cpu['name']}' which is using {top_cpu['cpu_percent']}% CPU")
        elif cpu > 70:
            status = "warning"
            issues.append(f"⚠ CPU usage is high at {cpu}%")
            recommendations.append("Close unnecessary applications to free up CPU resources")
        
        # Memory Analysis
        if mem > 90:
            status = "critical"
            issues.append(f"🔴 Memory is critically low - only {stats['memory']['available_gb']}GB free")
            top_mem = processes['top_memory'][0] if processes['top_memory'] else None
            if top_mem:
                recommendations.append(f"'{top_mem['name']}' is using {top_mem['memory_percent']}% of memory - consider closing it")
        elif mem > 80:
            if status != "critical":
                status = "warning"
            issues.append(f"⚠ Memory usage is high at {mem}%")
            recommendations.append("Close browser tabs or unused applications to free up RAM")
        
        # Disk Analysis
        if disk > 95:
            status = "critical"
            issues.append(f"🔴 Disk space critically low - only {stats['disk']['free_gb']}GB remaining")
            recommendations.append("Delete unnecessary files or move data to external storage")
            recommendations.append("Use the 'Clean Temp Files' button to free up space")
        elif disk > 85:
            if status == "healthy":
                status = "warning"
            issues.append(f"⚠ Disk space running low at {disk}%")
            recommendations.append("Consider cleaning up old files and running disk cleanup")
        
        # Generate summary
        if status == "healthy":
            summary = "✅ Your system is running smoothly! All resources are within normal ranges."
        elif status == "warning":
            summary = "⚠ Your system needs attention. Some resources are running high."
        else:
            summary = "🔴 Your system is under heavy load and needs immediate attention!"
        
        # Process insights
        process_insights = []
        if processes['top_cpu']:
            top3_cpu = processes['top_cpu'][:3]
            cpu_names = [p['name'] for p in top3_cpu]
            process_insights.append(f"Top CPU consumers: {', '.join(cpu_names)}")
        
        if processes['top_memory']:
            top3_mem = processes['top_memory'][:3]
            mem_names = [p['name'] for p in top3_mem]
            process_insights.append(f"Top memory consumers: {', '.join(mem_names)}")
        
        return {
            "status": status,
            "summary": summary,
            "issues": issues,
            "recommendations": recommendations,
            "process_insights": process_insights,
            "performance_score": SystemAnalyzer._calculate_score(cpu, mem, disk)
        }
    
    @staticmethod
    def _calculate_score(cpu, mem, disk):
        """Calculate overall performance score (0-100)"""
        cpu_score = max(0, 100 - cpu)
        mem_score = max(0, 100 - mem)
        disk_score = max(0, 100 - disk)
        return round((cpu_score + mem_score + disk_score) / 3, 1)

analyzer = SystemAnalyzer()
ai_chat = AIChat()

@app.route('/')
def home():
    """Basic endpoint to confirm server is running"""
    return jsonify({
        "message": "ClarityPC.AI server is live!",
        "status": "operational",
        "version": "0.5.0",
        "endpoints": [
            "/system/all",
            "/processes/top", 
            "/ai/analyze",
            "/ai/chat (POST)",
            "/actions/cleanup (POST)"
        ]
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"})

@app.route('/system/all')
def all_stats():
    """Get all system statistics in one call"""
    cpu_percent = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('C:\\')
    
    return jsonify({
        "cpu": {
            "usage_percent": cpu_percent,
            "core_count": psutil.cpu_count()
        },
        "memory": {
            "total_gb": round(mem.total / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "percent_used": mem.percent
        },
        "disk": {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "percent_used": disk.percent
        }
    })

@app.route('/processes/top')
def top_processes():
    """Get top processes by CPU and memory usage"""
    processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
        try:
            pinfo = proc.info
            processes.append({
                'pid': pinfo['pid'],
                'name': pinfo['name'],
                'cpu_percent': round(pinfo['cpu_percent'] or 0, 1),
                'memory_percent': round(pinfo['memory_percent'] or 0, 1),
                'status': pinfo['status']
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    top_cpu = sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)[:10]
    top_mem = sorted(processes, key=lambda x: x['memory_percent'], reverse=True)[:10]
    
    return jsonify({
        "top_cpu": top_cpu,
        "top_memory": top_mem,
        "total_processes": len(processes)
    })

@app.route('/ai/analyze')
def ai_analyze():
    """Get AI analysis of current system state"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('C:\\')
        
        stats = {
            "cpu": {"usage_percent": cpu_percent, "core_count": psutil.cpu_count()},
            "memory": {
                "total_gb": round(mem.total / (1024**3), 2),
                "used_gb": round(mem.used / (1024**3), 2),
                "available_gb": round(mem.available / (1024**3), 2),
                "percent_used": mem.percent
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent_used": disk.percent
            }
        }
        
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                pinfo = proc.info
                processes.append({
                    'pid': pinfo['pid'],
                    'name': pinfo['name'],
                    'cpu_percent': round(pinfo['cpu_percent'] or 0, 1),
                    'memory_percent': round(pinfo['memory_percent'] or 0, 1)
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        process_data = {
            "top_cpu": sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)[:10],
            "top_memory": sorted(processes, key=lambda x: x['memory_percent'], reverse=True)[:10]
        }
        
        analysis = analyzer.analyze_system(stats, process_data)
        
        return jsonify({
            "success": True,
            "analysis": analysis,
            "timestamp": psutil.boot_time()
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/ai/chat', methods=['POST'])
def ai_chat_endpoint():
    """Chat with AI about system performance"""
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        
        if not user_message:
            return jsonify({
                "success": False,
                "message": "No message provided"
            }), 400
        
        # Get current system stats
        cpu_percent = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('C:\\')
        
        stats = {
            "cpu": {"usage_percent": cpu_percent, "core_count": psutil.cpu_count()},
            "memory": {
                "total_gb": round(mem.total / (1024**3), 2),
                "used_gb": round(mem.used / (1024**3), 2),
                "available_gb": round(mem.available / (1024**3), 2),
                "percent_used": mem.percent
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent_used": disk.percent
            }
        }
        
        # Get process info
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                pinfo = proc.info
                processes.append({
                    'pid': pinfo['pid'],
                    'name': pinfo['name'],
                    'cpu_percent': round(pinfo['cpu_percent'] or 0, 1),
                    'memory_percent': round(pinfo['memory_percent'] or 0, 1)
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        process_data = {
            "top_cpu": sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)[:10],
            "top_memory": sorted(processes, key=lambda x: x['memory_percent'], reverse=True)[:10]
        }
        
        # Get AI response
        result = ai_chat.chat(user_message, stats, process_data)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500

@app.route('/processes/kill/<int:pid>', methods=['POST'])
def kill_process(pid):
    """Kill a process by PID"""
    try:
        proc = psutil.Process(pid)
        proc_name = proc.name()
        proc.terminate()
        proc.wait(timeout=3)
        
        return jsonify({
            "success": True,
            "message": f"Process '{proc_name}' (PID: {pid}) terminated successfully"
        })
    except psutil.NoSuchProcess:
        return jsonify({
            "success": False,
            "message": f"Process with PID {pid} not found"
        }), 404
    except psutil.AccessDenied:
        return jsonify({
            "success": False,
            "message": f"Access denied. Try running as administrator."
        }), 403
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500

@app.route('/actions/cleanup', methods=['POST'])
def cleanup_system():
    """Perform basic system cleanup"""
    results = []
    
    try:
        temp_path = os.environ.get('TEMP')
        if temp_path:
            deleted_count = 0
            deleted_size = 0
            
            for root, dirs, files in os.walk(temp_path):
                for file in files:
                    try:
                        file_path = os.path.join(root, file)
                        file_size = os.path.getsize(file_path)
                        os.remove(file_path)
                        deleted_count += 1
                        deleted_size += file_size
                    except:
                        pass
            
            size_mb = round(deleted_size / (1024**2), 2)
            results.append(f"Cleaned {deleted_count} files ({size_mb}MB)")
        
        return jsonify({
            "success": True,
            "results": results
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Cleanup error: {str(e)}"
        }), 500

def open_browser():
    time.sleep(2)
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == '__main__':
    print("🚀 ClarityPC.AI Backend Starting...")
    print("📍 Server running at: http://localhost:5000")
    print("🛑 Press CTRL+C to stop")
    print("\n📊 Available Endpoints:")
    print("   • http://localhost:5000/ - Status")
    print("   • http://localhost:5000/system/all - All stats")
    print("   • http://localhost:5000/processes/top - Top processes")
    print("   • http://localhost:5000/ai/analyze - AI system analysis")
    print("   • http://localhost:5000/ai/chat - AI chat (POST)")
    print("   • http://localhost:5000/actions/cleanup - System cleanup (POST)\n")

    threading.Timer(1.5, open_browser).start()
    app.run(debug=False, host='127.0.0.1', port=5000)
