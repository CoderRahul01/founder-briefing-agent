from beanie import Document, Indexed
from pydantic import Field
from typing import Optional, List
from datetime import datetime


class User(Document):
    email:            str
    stripe_key:       Optional[str]  = None           # User's personal key for revenue tracking
    gmail_token:      Optional[str]  = None
    competitor_list:  str            = 'Linear,Notion,Asana'
    delivery_email:   Optional[str]  = None
    whatsapp_number:  Optional[str]  = None
    
    # Billing Info (Platform Monetization)
    plan:                   str            = 'solo'   # solo / founder / team
    stripe_customer_id:     Optional[str]  = None
    stripe_subscription_id: Optional[str]  = None
    
    is_active:        bool           = True
    created_at:       datetime       = Field(default_factory=datetime.utcnow)
    last_brief_at:    Optional[datetime] = None
    
    # Usage Tracking
    manual_triggers_used:    int                = 0
    manual_trigger_reset_at: Optional[datetime] = None

    class Settings:
        name = 'users'


class Brief(Document):
    user_email:           str
    brief_text:           str
    date:                 str
    revenue_summary:      Optional[str]  = None
    emails_seen:          List[str]      = []
    competitor_headlines: List[str]      = []
    delivery_status:      str            = 'sent'
    created_at:           datetime       = Field(default_factory=datetime.utcnow)

    class Settings:
        name = 'briefs'


class AuditLog(Document):
    user_email:  str
    event_type:  str
    status:      str
    message:     Optional[str] = None
    metadata:    dict          = {}
    created_at:  datetime      = Field(default_factory=datetime.utcnow)

    class Settings:
        name = 'audit_logs'
