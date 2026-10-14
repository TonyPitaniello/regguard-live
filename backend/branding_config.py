"""
RegGuard Branding Configuration
Centralized color schemes, fonts, logos, and styling
"""

from typing import Tuple, Dict, Any
from dataclasses import dataclass

# Color palette (RGB tuples)
@dataclass
class ColorScheme:
    """Color definitions for RegGuard branding"""
    
    # Primary colors
    primary_indigo = (99, 102, 241)  # Main brand color
    primary_purple = (139, 92, 246)  # Secondary brand
    primary_blue = (59, 130, 246)    # Accent blue
    
    # Status colors
    success_green = (34, 197, 94)    # Low risk / Success
    warning_yellow = (234, 179, 8)   # Medium risk / Warning
    danger_red = (239, 68, 68)       # High risk / Danger
    critical_dark_red = (220, 38, 38) # Critical risk
    
    # Neutral colors
    white = (255, 255, 255)
    light_gray = (249, 250, 251)
    gray = (156, 163, 175)
    dark_gray = (75, 85, 99)
    text_dark = (30, 30, 30)
    
    # Utility colors
    divider = (229, 231, 235)
    background = (249, 250, 251)
    border = (209, 213, 219)


@dataclass
class FontScheme:
    """Font configuration"""
    
    # Font family
    font_family = "Helvetica"  # Standard PDF font (no embedding needed)
    
    # Heading fonts
    heading_large = ("Helvetica", "B", 24)  # Main heading
    heading_medium = ("Helvetica", "B", 16)  # Section heading
    heading_small = ("Helvetica", "B", 12)  # Subsection
    
    # Body fonts
    body_normal = ("Helvetica", "", 10)     # Regular text
    body_small = ("Helvetica", "", 9)       # Small text
    body_tiny = ("Helvetica", "", 8)        # Tiny text
    
    # Emphasis
    body_bold = ("Helvetica", "B", 10)
    body_italic = ("Helvetica", "I", 10)
    body_bold_italic = ("Helvetica", "BI", 10)


# Risk level styling
RISK_LEVEL_STYLES = {
    "LOW": {
        "color": ColorScheme.success_green,
        "label": "Low Risk",
        "description": "Minimal environmental/regulatory concerns",
    },
    "MEDIUM": {
        "color": ColorScheme.warning_yellow,
        "label": "Medium Risk",
        "description": "Some environmental/regulatory considerations",
    },
    "HIGH": {
        "color": ColorScheme.danger_red,
        "label": "High Risk",
        "description": "Significant environmental/regulatory concerns",
    },
    "CRITICAL": {
        "color": ColorScheme.critical_dark_red,
        "label": "Critical Risk",
        "description": "Serious environmental/regulatory issues requiring immediate attention",
    },
}

# Priority level styling
PRIORITY_STYLES = {
    "CRITICAL": {
        "color": ColorScheme.critical_dark_red,
        "icon": "⚠️",
        "label": "CRITICAL",
    },
    "HIGH": {
        "color": ColorScheme.danger_red,
        "icon": "🔴",
        "label": "HIGH",
    },
    "MEDIUM": {
        "color": ColorScheme.warning_yellow,
        "icon": "🟡",
        "label": "MEDIUM",
    },
    "LOW": {
        "color": ColorScheme.success_green,
        "icon": "🟢",
        "label": "LOW",
    },
}

# PDF page styling
PDF_MARGINS = {
    "top": 15,
    "right": 15,
    "bottom": 15,
    "left": 15,
}

PDF_HEADER_HEIGHT = 60
PDF_FOOTER_HEIGHT = 20

# Company branding text
COMPANY_NAME = "RegGuard"
COMPANY_TAGLINE = "Site Diligence Intelligence"
COMPANY_WEBSITE = "app.regguardagent.com"
COMPANY_EMAIL = "support@regguardagent.com"

# Footer text
FOOTER_TEXT = "© 2026 RegGuard. All rights reserved. This report is confidential and intended for authorized use only."
FOOTER_LINK = "Learn more: app.regguardagent.com"

# Header template
HEADER_TEMPLATE = {
    "left_text": COMPANY_NAME,
    "left_subtext": COMPANY_TAGLINE,
    "center_logo": "regguard_logo.png",  # Would be embedded in production
    "right_text": "Professional Report",
}

# Environmental categories styling
CATEGORY_STYLES = {
    "wetlands": {
        "icon": "🌿",
        "color": ColorScheme.primary_blue,
        "full_name": "Wetlands Assessment",
    },
    "endangered_species": {
        "icon": "🦅",
        "color": ColorScheme.primary_blue,
        "full_name": "Endangered Species Analysis",
    },
    "flood_zones": {
        "icon": "🌊",
        "color": ColorScheme.primary_blue,
        "full_name": "Flood Zone Mapping",
    },
    "noise_ordinances": {
        "icon": "📢",
        "color": ColorScheme.primary_blue,
        "full_name": "Noise Ordinance Review",
    },
    "nepa": {
        "icon": "📋",
        "color": ColorScheme.primary_blue,
        "full_name": "NEPA Compliance",
    },
    "state_requirements": {
        "icon": "📜",
        "color": ColorScheme.primary_blue,
        "full_name": "State Requirements",
    },
}

# Page layout configuration
PAGE_LAYOUT = {
    "standard": {
        "width": 210,  # A4
        "height": 297,  # A4
        "orientation": "P",  # Portrait
    },
    "landscape": {
        "width": 297,
        "height": 210,
        "orientation": "L",  # Landscape
    },
}

# Table styling
TABLE_STYLE = {
    "header_bg": ColorScheme.primary_indigo,
    "header_text": ColorScheme.white,
    "row_bg_alt": ColorScheme.light_gray,
    "border_color": ColorScheme.divider,
    "border_width": 0.1,
    "cell_padding": 3,
    "row_height": 8,
}

# List styling
LIST_STYLE = {
    "bullet": "•",
    "indent": 5,
    "spacing": 4,
    "colors": {
        "critical": ColorScheme.critical_dark_red,
        "high": ColorScheme.danger_red,
        "medium": ColorScheme.warning_yellow,
        "low": ColorScheme.success_green,
    },
}

# Report types
REPORT_TYPES = {
    "memo": {
        "title": "Site Diligence Research Memo",
        "description": "Environmental findings summary",
        "pages": "1-3",
        "focus": ["environmental", "summary", "email-friendly"],
    },
    "punch_list": {
        "title": "Action Plan: Comprehensive Punch List",
        "description": "Detailed action items with prioritization",
        "pages": "1+",
        "focus": ["actions", "timeline", "costs"],
    },
    "permits": {
        "title": "Permit Package",
        "description": "State-specific permit applications (pre-filled)",
        "pages": "1-10",
        "focus": ["permits", "state-specific", "submission-ready"],
    },
}

# Template configurations per state
STATE_CONFIGURATIONS = {
    "TX": {
        "name": "Texas",
        "authority": "City of [City] Building Department",
        "key_codes": ["International Energy Conservation Code (IECC)", "Texas Building Code"],
        "estimated_timeline": "2-4 weeks",
        "typical_fee": "$500-$5,000",
    },
    "CA": {
        "name": "California",
        "authority": "County Planning Department",
        "key_codes": ["California Building Code", "California Energy Code"],
        "estimated_timeline": "4-8 weeks",
        "typical_fee": "$2,000-$10,000",
    },
    "NY": {
        "name": "New York",
        "authority": "NYC Department of Buildings",
        "key_codes": ["NYC Building Code", "New York State Building Code"],
        "estimated_timeline": "3-6 weeks",
        "typical_fee": "$1,000-$8,000",
    },
}

def get_risk_color(risk_level: str) -> Tuple[int, int, int]:
    """Get RGB color for risk level"""
    return RISK_LEVEL_STYLES.get(risk_level, {}).get("color", ColorScheme.gray)

def get_priority_icon(priority: str) -> str:
    """Get icon for priority level"""
    return PRIORITY_STYLES.get(priority, {}).get("icon", "•")

def get_category_style(category: str) -> Dict[str, Any]:
    """Get styling for environmental category"""
    return CATEGORY_STYLES.get(category, {
        "icon": "📌",
        "color": ColorScheme.primary_blue,
        "full_name": category.replace("_", " ").title(),
    })

def get_state_config(state_code: str) -> Dict[str, Any]:
    """Get configuration for specific state"""
    return STATE_CONFIGURATIONS.get(state_code.upper(), {
        "name": "Other State",
        "authority": "Local Authority Having Jurisdiction",
        "key_codes": ["Local building codes"],
        "estimated_timeline": "2-6 weeks",
        "typical_fee": "$500-$5,000",
    })
