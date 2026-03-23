"""
PDF Generation Service for PG Result Marksheets
Uses WeasyPrint for HTML to PDF conversion
"""

import os
import base64
from django.conf import settings
from django.template.loader import get_template
from weasyprint import HTML, CSS


class PGMarksheetPDFGenerator:
    """
    Generate PDF marksheets for PG results
    """
    
    def __init__(self):
        # WeasyPrint configuration
        self.css = CSS(string=self._get_css())
    
    def _get_university_logo_base64(self) -> str:
        """
        Load university logo and convert to base64
        """
        try:
            logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'purnea-logo.png')
            if os.path.exists(logo_path):
                with open(logo_path, 'rb') as image_file:
                    return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            print(f"Error loading logo: {e}")
        return ""

    def _get_controller_sign_base64(self) -> str:
        """
        Load controller signature and convert to base64
        """
        try:
            sign_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'controller-of-examination-signature.png')
            if os.path.exists(sign_path):
                with open(sign_path, 'rb') as image_file:
                    return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            print(f"Error loading signature: {e}")
        return ""
    
    def _get_css(self) -> str:
        """Get CSS styling for PDF"""
        return """
        @page {
            size: A4;
            margin: 1cm;
            @top-center {
                content: "PG Result Marksheet";
                font-size: 12px;
                color: #666;
            }
            @bottom-center {
                content: "Page " counter(page) " of " counter(pages);
                font-size: 10px;
                color: #666;
            }
        }
        
        body {
            font-family: 'Arial', sans-serif;
            font-size: 12px;
            line-height: 1.4;
            color: #333;
        }
        
        .header {
            text-align: center;
            margin-bottom: 20px;
            border-bottom: 2px solid #333;
            padding-bottom: 10px;
        }
        
        .student-info {
            margin-bottom: 20px;
        }
        
        .info-row {
            display: flex;
            margin-bottom: 5px;
        }
        
        .info-label {
            font-weight: bold;
            width: 150px;
        }
        
        .info-value {
            flex: 1;
        }
        
        .results-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        
        .results-table th,
        .results-table td {
            border: 1px solid #333;
            padding: 8px;
            text-align: left;
            font-size: 11px;
        }
        
        .results-table th {
            background-color: #f0f0f0;
            font-weight: bold;
        }
        
        .footer {
            margin-top: 30px;
            text-align: center;
            font-size: 10px;
            color: #666;
        }
        
        .grade-pass {
            color: #28a745;
            font-weight: bold;
        }
        
        .grade-fail {
            color: #dc3545;
            font-weight: bold;
        }
        
        .sgpa-box {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            padding: 10px;
            margin: 20px 0;
            text-align: center;
        }
        
        .page-break {
            page-break-after: always;
        }
        """
    
    def generate_pdf(self, result_data: dict) -> bytes:
        """
        Generate PDF from result data
        
        Args:
            result_data: Result data from calculator
            
        Returns:
            PDF bytes
        """
        try:
            # Add images to result data
            result_data['university_logo'] = self._get_university_logo_base64()
            result_data['controller_sign'] = self._get_controller_sign_base64()
            
            # Render HTML template
            template = get_template('pgoldresult/marksheet_pdf.html')
            html_content = template.render(result_data)
            
            # Generate PDF without external CSS (use template CSS only)
            html_doc = HTML(string=html_content)
            pdf_bytes = html_doc.write_pdf()
            
            return pdf_bytes
            
        except Exception as e:
            print(f"PDF generation error: {e}")
            # Fallback to basic HTML if WeasyPrint fails
            return self._generate_fallback_pdf(result_data)
    
    def _generate_fallback_pdf(self, result_data: dict) -> bytes:
        """
        Fallback PDF generation using basic HTML
        """
        template = get_template('pgoldresult/marksheet_pdf.html')
        html_content = template.render(result_data)
        
        # Convert HTML to basic PDF string (this is a simplified version)
        html_doc = HTML(string=html_content)
        return html_doc.write_pdf(stylesheet=self.css)
    
    def generate_filename(self, student_info: dict, semester: str, session: str) -> str:
        """
        Generate filename for PDF
        """
        reg_no = student_info.get('registration_no', 'UNKNOWN')
        name = student_info.get('name', 'Student').replace(' ', '_')
        return f"PG_Result_{name}_{reg_no}_{semester}_{session}.pdf"


def generate_marksheet_pdf(result_data: dict) -> tuple:
    """
    Convenience function to generate PDF marksheet
    
    Args:
        result_data: Result data from calculator
        
    Returns:
        Tuple of (pdf_bytes, filename)
    """
    generator = PGMarksheetPDFGenerator()
    
    # Generate PDF
    pdf_bytes = generator.generate_pdf(result_data)
    
    # Generate filename
    filename = generator.generate_filename(
        result_data.get('student_info', {}),
        result_data.get('semester', ''),
        result_data.get('session', '')
    )
    
    return pdf_bytes, filename
