import os
import json
import requests
from urllib.parse import urlparse, parse_qs
from flask import Flask, render_template_string, request, jsonify
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)

class SheerIDBackendEngine:
    def __init__(self, verify_url):
        self.verify_url = verify_url
        self.parsed_url = urlparse(verify_url)
        self.program_id = self._extract_path_segment('verify')
        self.verification_id = self._extract_query_param('verificationId')
        
        self.base_api = "https://services.sheerid.com/rest/v2"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://services.sheerid.com",
            "Referer": verify_url
        })

    def _extract_path_segment(self, segment_name):
        parts = self.parsed_url.path.split('/')
        for i, part in enumerate(parts):
            if part == segment_name and i + 1 < len(parts):
                return parts[i + 1]
        return None

    def _extract_query_param(self, param_name):
        query_params = parse_qs(self.parsed_url.query)
        if param_name in query_params:
            return query_params[param_name][0]
        return None

    def search_organization(self, school_name, country="US"):
        search_url = f"{self.base_api}/organization/search"
        params = {"name": school_name, "country": country}
        response = self.session.get(search_url, params=params)
        if response.status_code == 200:
            orgs = response.json()
            if orgs:
                return orgs[0].get('id')
        return None

    def submit_personal_info(self, first_name, last_name, email, birth_date, organization_id):
        endpoint = f"{self.base_api}/verification/{self.verification_id}/step/collectStudentPersonalInfo"
        payload = {
            "firstName": first_name,
            "lastName": last_name,
            "email": email,
            "birthDate": birth_date,
            "organization": {"id": organization_id}
        }
        response = self.session.post(endpoint, data=json.dumps(payload))
        if response.status_code == 200:
            return response.json()
        return None

    def generate_student_document(self, first_name, last_name, school_name, output_path="/tmp/enrollment_doc.jpg"):
        width, height = 1200, 800
        image = Image.new("RGB", (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(image)
        
        try:
            font_title = ImageFont.truetype("arial.ttf", 36)
            font_bold = ImageFont.truetype("arial.ttf", 24)
            font_regular = ImageFont.truetype("arial.ttf", 22)
        except IOError:
            font_title = ImageFont.load_default()
            font_bold = ImageFont.load_default()
            font_regular = ImageFont.load_default()

        draw.rectangle([(0, 0), (width, 120)], fill=(15, 23, 42))
        draw.text((50, 40), f"{school_name.upper()} - OFFICIAL ENROLLMENT VERIFICATION", fill=(255, 255, 255), font=font_title)
        
        fields = [
            ("Student Name:", f"{first_name} {last_name}"),
            ("Enrollment Status:", "Enrolled / Active Full-Time Student"),
            ("Academic Term:", "Fall 2026 / Spring 2027 Semester"),
            ("Institution:", school_name),
            ("Document Type:", "Official Enrollment Receipt & Status Certification")
        ]
        
        y_offset = 180
        for label, val in fields:
            draw.text((60, y_offset), label, fill=(100, 116, 139), font=font_bold)
            draw.text((350, y_offset), val, fill=(15, 23, 42), font=font_regular)
            y_offset += 60

        draw.line([(60, 650), (1140, 650)], fill=(203, 213, 225), width=2)
        draw.text((60, 680), "This document was dynamically generated for institutional verification compliance.", fill=(148, 163, 184), font=font_regular)
        
        image.save(output_path, "JPEG", quality=95)
        return output_path

    def upload_document(self, file_path):
        endpoint = f"{self.base_api}/verification/{self.verification_id}/step/docUpload"
        with open(file_path, 'rb') as f:
            files = {'files': (os.path.basename(file_path), f, 'image/jpeg')}
            response = self.session.post(endpoint, files=files)
        if response.status_code == 200:
            return response.json()
        return None

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <title>SheerID Vercel Panel</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex items-center justify-center p-4">
    <div class="w-full max-w-xl bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl">
        <h1 class="text-xl font-bold text-emerald-400 mb-1">SheerID Vercel Bridge</h1>
        <p class="text-xs text-slate-400 mb-6">Serverless State Machine Executor</p>
        
        <form id="verifyForm" class="space-y-4">
            <div>
                <label class="block text-xs text-slate-400 mb-1">Verification URL</label>
                <input type="text" id="url" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-sm text-slate-200" value="https://services.sheerid.com/verify/67c8c14f5f17a83b745e3f82/?verificationId=69bc46412384a">
            </div>
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="block text-xs text-slate-400 mb-1">First Name</label>
                    <input type="text" id="firstName" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-sm text-slate-200" value="Alex">
                </div>
                <div>
                    <label class="block text-xs text-slate-400 mb-1">Last Name</label>
                    <input type="text" id="lastName" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-sm text-slate-200" value="Smith">
                </div>
            </div>
            <div>
                <label class="block text-xs text-slate-400 mb-1">School Name</label>
                <input type="text" id="schoolName" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-sm text-slate-200" value="Arizona State University">
            </div>
            <div>
                <label class="block text-xs text-slate-400 mb-1">Email (.edu)</label>
                <input type="text" id="email" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-sm text-slate-200" value="asmith@asu.edu">
            </div>
            <div>
                <label class="block text-xs text-slate-400 mb-1">Birth Date</label>
                <input type="text" id="birthDate" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-sm text-slate-200" value="2001-05-14">
            </div>
            <button type="button" onclick="runVerification()" class="w-full bg-emerald-600 hover:bg-emerald-500 font-medium py-2.5 rounded-lg text-sm text-white transition-all">
                Execute Verification Flow
            </button>
        </form>
        
        <div id="result" class="mt-6 hidden bg-slate-950 border border-slate-800 rounded-xl p-4 font-mono text-xs space-y-2"></div>
    </div>

    <script>
        async function runVerification() {
            const data = {
                url: document.getElementById('url').value,
                firstName: document.getElementById('firstName').value,
                lastName: document.getElementById('lastName').value,
                schoolName: document.getElementById('schoolName').value,
                email: document.getElementById('email').value,
                birthDate: document.getElementById('birthDate').value
            };

            const resDiv = document.getElementById('result');
            resDiv.classList.remove('hidden');
            resDiv.innerHTML = '<span class="text-yellow-400">[*] Processing serverless handshake...</span>';

            const response = await fetch('/api/index', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            const json = await response.json();
            
            if(json.success) {
                resDiv.innerHTML = `
                    <div class="text-emerald-400 font-bold">✅ Step Completed: ${json.step}</div>
                    <div class="text-slate-300">Redirect Link: <a href="${json.redirectUrl || '#'}" target="_blank" class="text-cyan-400 underline">${json.redirectUrl || 'N/A'}</a></div>
                `;
            } else {
                resDiv.innerHTML = `<div class="text-red-400 font-bold">❌ Error: ${json.error}</div>`;
            }
        }
    </script>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/index', methods=['POST'])
def api_verify():
    req = request.json
    try:
        engine = SheerIDBackendEngine(req['url'])
        org_id = engine.search_organization(req['schoolName'])
        if not org_id:
            return jsonify({"success": False, "error": "Organization not found"})
        
        result = engine.submit_personal_info(
            req['firstName'], req['lastName'], req['email'], req['birthDate'], org_id
        )
        
        if not result:
            return jsonify({"success": False, "error": "API submission failed"})
            
        current_step = result.get('currentStep')
        
        if current_step == 'docUpload':
            doc_path = engine.generate_student_document(req['firstName'], req['lastName'], req['schoolName'])
            doc_result = engine.upload_document(doc_path)
            if doc_result:
                current_step = doc_result.get('currentStep')
                result = doc_result

        return jsonify({
            "success": True,
            "step": current_step,
            "redirectUrl": result.get('redirectUrl')
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == '__main__':
    app.run()
