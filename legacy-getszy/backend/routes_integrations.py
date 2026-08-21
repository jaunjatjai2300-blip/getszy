"""Integrations Marketplace — catalog, connection status, and OAuth stubs.

Users can browse integrations, connect/disconnect, and view connection status.
Admins can manage the catalog and see usage analytics.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth import get_current_user, get_current_admin
from db import db

router = APIRouter(tags=['integrations'])


# ═══════════════════════════════════════════════════════════════════════════════
# Integration Catalog (comprehensive list)
# ═══════════════════════════════════════════════════════════════════════════════

INTEGRATIONS = [
    # ── Communication ──
    {'id': 'gmail', 'name': 'Gmail', 'category': 'communication', 'description': 'Google\'s email service with spam protection, search, and G Suite integration.', 'icon': '📧', 'color': '#EA4335', 'auth_type': 'oauth', 'provider': 'google'},
    {'id': 'outlook', 'name': 'Outlook', 'category': 'communication', 'description': 'Microsoft\'s email and calendaring platform integrating contacts and scheduling.', 'icon': '📨', 'color': '#0078D4', 'auth_type': 'oauth', 'provider': 'microsoft'},
    {'id': 'slack', 'name': 'Slack', 'category': 'communication', 'description': 'Channel-based messaging platform for team collaboration and tool integration.', 'icon': '💬', 'color': '#4A154B', 'auth_type': 'oauth', 'provider': 'slack'},
    {'id': 'slackbot', 'name': 'Slackbot', 'category': 'communication', 'description': 'Workspace-wide read access to Slack for searching messages, files, and channel history.', 'icon': '🤖', 'color': '#4A154B', 'auth_type': 'oauth', 'provider': 'slack'},
    {'id': 'discord', 'name': 'Discord', 'category': 'communication', 'description': 'Instant messaging and VoIP social platform for communities.', 'icon': '🎮', 'color': '#5865F2', 'auth_type': 'oauth', 'provider': 'discord'},
    {'id': 'discord-bot', 'name': 'Discord Bot', 'category': 'communication', 'description': 'Automated programs for moderation, music playback, and user engagement.', 'icon': '🤖', 'color': '#5865F2', 'auth_type': 'bot_token'},
    {'id': 'microsoft-teams', 'name': 'Microsoft Teams', 'category': 'communication', 'description': 'Chat, video meetings, and file storage within Microsoft 365.', 'icon': '👥', 'color': '#6264A7', 'auth_type': 'oauth', 'provider': 'microsoft'},
    {'id': 'whatsapp', 'name': 'WhatsApp', 'category': 'communication', 'description': 'WhatsApp Business API for messaging and automation. Business accounts only.', 'icon': '📱', 'color': '#25D366', 'auth_type': 'api_key'},
    {'id': 'telegram', 'name': 'Telegram', 'category': 'communication', 'description': 'Cloud-based messaging with bot API support.', 'icon': '✈️', 'color': '#0088CC', 'auth_type': 'bot_token'},
    {'id': 'zoom', 'name': 'Zoom', 'category': 'communication', 'description': 'Video conferencing with breakout rooms, screen sharing, and integrations.', 'icon': '📹', 'color': '#2D8CFF', 'auth_type': 'oauth', 'provider': 'zoom'},

    # ── CRM & Sales ──
    {'id': 'hubspot', 'name': 'HubSpot', 'category': 'crm', 'description': 'Inbound marketing, sales, and customer service platform with CRM and analytics.', 'icon': '🟠', 'color': '#FF7A59', 'auth_type': 'oauth', 'provider': 'hubspot'},
    {'id': 'salesforce', 'name': 'Salesforce', 'category': 'crm', 'description': 'Leading CRM platform integrating sales, service, marketing, and analytics.', 'icon': '☁️', 'color': '#00A1E0', 'auth_type': 'oauth', 'provider': 'salesforce'},
    {'id': 'zoho-crm', 'name': 'Zoho CRM', 'category': 'crm', 'description': 'Suite of cloud applications including CRM, email marketing, and collaboration.', 'icon': '🔴', 'color': '#E42527', 'auth_type': 'oauth', 'provider': 'zoho'},
    {'id': 'zoho-big', 'name': 'Zoho Bigin', 'category': 'crm', 'description': 'Simplified CRM for small businesses focusing on pipeline tracking.', 'icon': '🔴', 'color': '#E42527', 'auth_type': 'oauth', 'provider': 'zoho'},
    {'id': 'dynamics365', 'name': 'Dynamics 365', 'category': 'crm', 'description': 'Microsoft CRM + ERP combining sales, marketing, and customer service.', 'icon': '🔵', 'color': '#002050', 'auth_type': 'oauth', 'provider': 'microsoft'},
    {'id': 'apollo', 'name': 'Apollo', 'category': 'crm', 'description': 'CRM and lead generation for discovering contacts and managing outreach.', 'icon': '🚀', 'color': '#6B4FBB', 'auth_type': 'api_key'},
    {'id': 'close', 'name': 'Close', 'category': 'crm', 'description': 'CRM for managing sales processes, calling, and email automation.', 'icon': '🔴', 'color': '#E63946', 'auth_type': 'api_key'},
    {'id': 'attio', 'name': 'Attio', 'category': 'crm', 'description': 'Fully customizable workspace for team relationships and workflows.', 'icon': '⬛', 'color': '#000000', 'auth_type': 'oauth'},
    {'id': 'capsule-crm', 'name': 'Capsule CRM', 'category': 'crm', 'description': 'Simple yet powerful CRM for managing customer relationships and sales.', 'icon': '💊', 'color': '#00A94F', 'auth_type': 'api_key'},
    {'id': 'pipedrive', 'name': 'Pipedrive', 'category': 'crm', 'description': 'Sales-focused CRM with pipeline management and activity tracking.', 'icon': '🟢', 'color': '#1B1C1E', 'auth_type': 'oauth'},

    # ── Project Management ──
    {'id': 'linear', 'name': 'Linear', 'category': 'project', 'description': 'Streamlined issue tracking with fast workflows and GitHub integrations.', 'icon': '📐', 'color': '#5E6AD2', 'auth_type': 'oauth'},
    {'id': 'jira', 'name': 'Jira', 'category': 'project', 'description': 'Bug tracking, issue tracking, and agile project management.', 'icon': '🔵', 'color': '#0052CC', 'auth_type': 'oauth', 'provider': 'atlassian'},
    {'id': 'asana', 'name': 'Asana', 'category': 'project', 'description': 'Tool to help teams organize, track, and manage their work.', 'icon': '🔴', 'color': '#F06A6A', 'auth_type': 'oauth'},
    {'id': 'trello', 'name': 'Trello', 'category': 'project', 'description': 'Web-based kanban-style list-making application.', 'icon': '📋', 'color': '#0079BF', 'auth_type': 'oauth', 'provider': 'atlassian'},
    {'id': 'monday', 'name': 'Monday.com', 'category': 'project', 'description': 'Customizable work management platform for project planning and automation.', 'icon': '🟣', 'color': '#FF3D57', 'auth_type': 'oauth'},
    {'id': 'clickup', 'name': 'ClickUp', 'category': 'project', 'description': 'Unified tasks, docs, goals, and chat in a single platform.', 'icon': '🟣', 'color': '#7B68EE', 'auth_type': 'oauth'},
    {'id': 'notion', 'name': 'Notion', 'category': 'project', 'description': 'Centralizes notes, docs, wikis, and tasks in a unified workspace.', 'icon': '📝', 'color': '#000000', 'auth_type': 'oauth'},
    {'id': 'confluence', 'name': 'Confluence', 'category': 'project', 'description': 'Team collaboration and knowledge management tool.', 'icon': '📘', 'color': '#172B4D', 'auth_type': 'oauth', 'provider': 'atlassian'},
    {'id': 'wrike', 'name': 'Wrike', 'category': 'project', 'description': 'Project management with Gantt charts, reporting, and resource management.', 'icon': '🟡', 'color': '#FFCD00', 'auth_type': 'oauth'},
    {'id': 'shortcut', 'name': 'Shortcut', 'category': 'project', 'description': 'Aligns product development with company objectives.', 'icon': '⚡', 'color': '#0052CC', 'auth_type': 'api_key'},
    {'id': 'basecamp', 'name': 'Basecamp', 'category': 'project', 'description': 'Project management and team collaboration tool.', 'icon': '🏕️', 'color': '#1D2D35', 'auth_type': 'oauth'},
    {'id': 'airtable', 'name': 'Airtable', 'category': 'project', 'description': 'Merges spreadsheet functionality with database power for team collaboration.', 'icon': '🟦', 'color': '#18BFFF', 'auth_type': 'oauth'},
    {'id': 'coda', 'name': 'Coda', 'category': 'project', 'description': 'Collaborative workspace transforming documents into powerful tools.', 'icon': '📄', 'color': '#F46A54', 'auth_type': 'oauth'},
    {'id': 'productboard', 'name': 'Productboard', 'category': 'project', 'description': 'Product management platform gathering feedback and prioritizing features.', 'icon': '🟧', 'color': '#0065FF', 'auth_type': 'oauth'},

    # ── Development ──
    {'id': 'github', 'name': 'GitHub', 'category': 'development', 'description': 'Code hosting platform for version control and collaboration.', 'icon': '🐙', 'color': '#181717', 'auth_type': 'oauth', 'provider': 'github'},
    {'id': 'gitlab', 'name': 'GitLab', 'category': 'development', 'description': 'DevOps platform with Git repository management and CI/CD.', 'icon': '🦊', 'color': '#FC6D26', 'auth_type': 'oauth'},
    {'id': 'bitbucket', 'name': 'Bitbucket', 'category': 'development', 'description': 'Git-based code hosting with pull requests and integrations.', 'icon': '🔵', 'color': '#0052CC', 'auth_type': 'oauth', 'provider': 'atlassian'},
    {'id': 'sentry', 'name': 'Sentry', 'category': 'development', 'description': 'Error tracking and monitoring for applications.', 'icon': '🔴', 'color': '#362D59', 'auth_type': 'api_key'},
    {'id': 'cloudflare', 'name': 'Cloudflare', 'category': 'development', 'description': 'Global network for security, performance, and reliability.', 'icon': '☁️', 'color': '#F38020', 'auth_type': 'api_key'},
    {'id': 'ngrok', 'name': 'Ngrok', 'category': 'development', 'description': 'Secure tunnels to locally hosted applications for testing.', 'icon': '🌐', 'color': '#1A1A2E', 'auth_type': 'api_key'},
    {'id': 'circleci', 'name': 'CircleCI', 'category': 'development', 'description': 'CI/CD platform for build, test, and deployment pipelines.', 'icon': '⭕', 'color': '#343434', 'auth_type': 'api_key'},
    {'id': 'buildkite', 'name': 'Buildkite', 'category': 'development', 'description': 'Fast CI/CD pipelines on your own infrastructure.', 'icon': '🔨', 'color': '#14CC80', 'auth_type': 'api_key'},
    {'id': 'launchdarkly', 'name': 'LaunchDarkly', 'category': 'development', 'description': 'Feature management platform using feature flags.', 'icon': '🚀', 'color': '#2D1B69', 'auth_type': 'api_key'},

    # ── Marketing & SEO ──
    {'id': 'google-ads', 'name': 'Google Ads', 'category': 'marketing', 'description': 'Online advertising platform for displaying ads to web users.', 'icon': '📢', 'color': '#4285F4', 'auth_type': 'oauth', 'provider': 'google'},
    {'id': 'google-analytics', 'name': 'Google Analytics', 'category': 'marketing', 'description': 'Website traffic tracking, user behavior, and conversion data.', 'icon': '📊', 'color': '#E37400', 'auth_type': 'oauth', 'provider': 'google'},
    {'id': 'semrush', 'name': 'Semrush', 'category': 'marketing', 'description': 'SEO tool suite for keyword research, competitor analysis, and ad optimization.', 'icon': '🟠', 'color': '#FF642D', 'auth_type': 'api_key'},
    {'id': 'ahrefs', 'name': 'Ahrefs', 'category': 'marketing', 'description': 'SEO platform with site audits, keyword research, and competitive insights.', 'icon': '🔵', 'color': '#0E9C4E', 'auth_type': 'api_key'},
    {'id': 'moz', 'name': 'Moz', 'category': 'marketing', 'description': 'SEO software with keyword research, site audits, and rank tracking.', 'icon': '🟦', 'color': '#00539B', 'auth_type': 'api_key'},
    {'id': 'mailchimp', 'name': 'Mailchimp', 'category': 'marketing', 'description': 'Email marketing with campaign templates, segmentation, and analytics.', 'icon': '🐵', 'color': '#FFE01B', 'auth_type': 'api_key'},
    {'id': 'mailerlite', 'name': 'MailerLite', 'category': 'marketing', 'description': 'Email marketing for campaigns, automation, and landing pages.', 'icon': '✉️', 'color': '#09C269', 'auth_type': 'api_key'},
    {'id': 'activecampaign', 'name': 'ActiveCampaign', 'category': 'marketing', 'description': 'Marketing automation and CRM for email campaigns and customer segmentation.', 'icon': '🔵', 'color': '#356AE6', 'auth_type': 'api_key'},
    {'id': 'sendgrid', 'name': 'SendGrid', 'category': 'marketing', 'description': 'Cloud-based email delivery for transactional and marketing emails.', 'icon': '📤', 'color': '#1A82E2', 'auth_type': 'api_key'},
    {'id': 'typefully', 'name': 'Typefully', 'category': 'marketing', 'description': 'Platform for creating and managing AI-powered content.', 'icon': '✍️', 'color': '#000000', 'auth_type': 'oauth'},
    {'id': 'heygen', 'name': 'HeyGen', 'category': 'marketing', 'description': 'AI video platform for streamlining video creation.', 'icon': '🎬', 'color': '#7C3AED', 'auth_type': 'api_key'},
    {'id': 'fomo', 'name': 'Fomo', 'category': 'marketing', 'description': 'Social proof notifications displaying real-time user activity.', 'icon': '🔔', 'color': '#FF6B35', 'auth_type': 'api_key'},
    {'id': 'toneden', 'name': 'ToneDen', 'category': 'marketing', 'description': 'Automates social media campaigns, advertising, and landing pages.', 'icon': '🎵', 'color': '#1A1A2E', 'auth_type': 'api_key'},

    # ── E-commerce ──
    {'id': 'shopify', 'name': 'Shopify', 'category': 'ecommerce', 'description': 'E-commerce platform for building online stores.', 'icon': '🛍️', 'color': '#96BF48', 'auth_type': 'oauth'},
    {'id': 'stripe', 'name': 'Stripe', 'category': 'ecommerce', 'description': 'Online payment infrastructure with fraud prevention and APIs.', 'icon': '💳', 'color': '#635BFF', 'auth_type': 'api_key'},
    {'id': 'razorpay', 'name': 'Razorpay', 'category': 'ecommerce', 'description': 'Indian payment gateway for businesses.', 'icon': '💰', 'color': '#072654', 'auth_type': 'api_key'},
    {'id': 'square', 'name': 'Square', 'category': 'ecommerce', 'description': 'Payment processing, POS systems, invoicing, and e-commerce tools.', 'icon': '⬜', 'color': '#006AFF', 'auth_type': 'oauth'},
    {'id': 'gumroad', 'name': 'Gumroad', 'category': 'ecommerce', 'description': 'Simplify selling digital goods and memberships.', 'icon': '🛒', 'color': '#FF90E8', 'auth_type': 'oauth'},
    {'id': 'opensea', 'name': 'OpenSea', 'category': 'ecommerce', 'description': 'World\'s first and largest NFT marketplace.', 'icon': '🌊', 'color': '#2081E2', 'auth_type': 'api_key'},
    {'id': 'pandadoc', 'name': 'PandaDoc', 'category': 'ecommerce', 'description': 'Document creation, e-signatures, and workflow automation.', 'icon': '🐼', 'color': '#47AFFF', 'auth_type': 'oauth'},
    {'id': 'jungle-scout', 'name': 'Jungle Scout', 'category': 'ecommerce', 'description': 'Amazon product research, sales estimates, and competitive insights.', 'icon': '🦁', 'color': '#FF6B00', 'auth_type': 'api_key'},

    # ── Finance & Accounting ──
    {'id': 'zoho-books', 'name': 'Zoho Books', 'category': 'finance', 'description': 'Accounting, invoicing, and expense tracking within Zoho ecosystem.', 'icon': '📕', 'color': '#E42527', 'auth_type': 'oauth', 'provider': 'zoho'},
    {'id': 'freshbooks', 'name': 'FreshBooks', 'category': 'finance', 'description': 'Cloud accounting for invoicing, expense tracking, and time management.', 'icon': '📗', 'color': '#0075DD', 'auth_type': 'oauth'},
    {'id': 'ynab', 'name': 'YNAB', 'category': 'finance', 'description': 'Budgeting tool for tracking expenses and planning finances.', 'icon': '💵', 'color': '#85C1E2', 'auth_type': 'oauth'},
    {'id': 'lexoffice', 'name': 'Lexoffice', 'category': 'finance', 'description': 'Cloud accounting for freelancers and small businesses.', 'icon': '📘', 'color': '#2E3192', 'auth_type': 'oauth'},
    {'id': 'altoviz', 'name': 'Altoviz', 'category': 'finance', 'description': 'Cloud-based billing and invoicing platform.', 'icon': '💲', 'color': '#00B4D8', 'auth_type': 'api_key'},

    # ── Data & Analytics ──
    {'id': 'google-bigquery', 'name': 'Google BigQuery', 'category': 'data', 'description': 'Fully managed data warehouse for large-scale analytics.', 'icon': '🏗️', 'color': '#4285F4', 'auth_type': 'oauth', 'provider': 'google'},
    {'id': 'mixpanel', 'name': 'Mixpanel', 'category': 'data', 'description': 'Product analytics tracking user interactions and engagement.', 'icon': '📊', 'color': '#7856FF', 'auth_type': 'api_key'},
    {'id': 'posthog', 'name': 'PostHog', 'category': 'data', 'description': 'Open-source product analytics for user behavior tracking.', 'icon': '🦔', 'color': '#1D4AFF', 'auth_type': 'api_key'},
    {'id': 'amplitude', 'name': 'Amplitude', 'category': 'data', 'description': 'Product analytics with cohort analysis and A/B testing.', 'icon': '📈', 'color': '#1B1F3B', 'auth_type': 'api_key'},
    {'id': 'hotjar', 'name': 'Hotjar', 'category': 'data', 'description': 'Heatmaps, session recordings, and user feedback.', 'icon': '🔥', 'color': '#FF3C00', 'auth_type': 'api_key'},
    {'id': 'microsoft-clarity', 'name': 'Microsoft Clarity', 'category': 'data', 'description': 'Free user behavior analytics with heatmaps and session recordings.', 'icon': '🔍', 'color': '#0078D4', 'auth_type': 'api_key'},
    {'id': 'klipfolio', 'name': 'Klipfolio', 'category': 'data', 'description': 'Cloud BI platform for real-time dashboards and reports.', 'icon': '📉', 'color': '#12B5D0', 'auth_type': 'api_key'},
    {'id': 'bigml', 'name': 'BigML', 'category': 'data', 'description': 'Machine learning platform for predictive models.', 'icon': '🧠', 'color': '#348DCA', 'auth_type': 'api_key'},
    {'id': 'datarobot', 'name': 'DataRobot', 'category': 'data', 'description': 'ML platform automating model building and deployment.', 'icon': '🤖', 'color': '#1F4397', 'auth_type': 'api_key'},

    # ── Support & Helpdesk ──
    {'id': 'zendesk', 'name': 'Zendesk', 'category': 'support', 'description': 'Customer support with ticketing, live chat, and knowledge base.', 'icon': '🟢', 'color': '#03363D', 'auth_type': 'oauth'},
    {'id': 'freshdesk', 'name': 'Freshdesk', 'category': 'support', 'description': 'Customer support with ticketing, knowledge base, and automation.', 'icon': '🟢', 'color': '#26A69A', 'auth_type': 'oauth'},
    {'id': 'intercom', 'name': 'Intercom', 'category': 'support', 'description': 'Live chat, messaging, and customer engagement tools.', 'icon': '💙', 'color': '#286EFA', 'auth_type': 'oauth'},
    {'id': 'gorgias', 'name': 'Gorgias', 'category': 'support', 'description': 'Helpdesk specializing in e-commerce with order management.', 'icon': '🟣', 'color': '#6C3BF5', 'auth_type': 'oauth'},
    {'id': 'zoho-desk', 'name': 'Zoho Desk', 'category': 'support', 'description': 'Context-aware helpdesk with ticket tracking and automation.', 'icon': '🔴', 'color': '#E42527', 'auth_type': 'oauth', 'provider': 'zoho'},

    # ── Design & Creative ──
    {'id': 'figma', 'name': 'Figma', 'category': 'design', 'description': 'Collaborative interface design tool.', 'icon': '🎨', 'color': '#A259FF', 'auth_type': 'oauth'},
    {'id': 'canva', 'name': 'Canva', 'category': 'design', 'description': 'Drag-and-drop design suite for social media graphics and presentations.', 'icon': '🖼️', 'color': '#00C4CC', 'auth_type': 'oauth'},
    {'id': 'miro', 'name': 'Miro', 'category': 'design', 'description': 'Collaborative online whiteboard for brainstorming and planning.', 'icon': '🟡', 'color': '#FFD02F', 'auth_type': 'oauth'},
    {'id': 'bannerbear', 'name': 'Bannerbear', 'category': 'design', 'description': 'Automated image and video generation API.', 'icon': '🐻', 'color': '#FF6B6B', 'auth_type': 'api_key'},
    {'id': 'tinypng', 'name': 'TinyPNG', 'category': 'design', 'description': 'Smart lossy compression for WebP, JPEG, and PNG files.', 'icon': '🐼', 'color': '#69B046', 'auth_type': 'api_key'},

    # ── Cloud Storage ──
    {'id': 'google-drive', 'name': 'Google Drive', 'category': 'storage', 'description': 'Cloud storage for uploading, sharing, and collaborating on files.', 'icon': '📁', 'color': '#4285F4', 'auth_type': 'oauth', 'provider': 'google'},
    {'id': 'onedrive', 'name': 'OneDrive', 'category': 'storage', 'description': 'Microsoft\'s cloud storage with sync and collaboration.', 'icon': '☁️', 'color': '#0078D4', 'auth_type': 'oauth', 'provider': 'microsoft'},
    {'id': 'dropbox', 'name': 'Dropbox', 'category': 'storage', 'description': 'Cloud storage with file syncing, sharing, and version control.', 'icon': '📦', 'color': '#0061FF', 'auth_type': 'oauth'},
    {'id': 'box', 'name': 'Box', 'category': 'storage', 'description': 'Cloud content management for secure file storage and collaboration.', 'icon': '📋', 'color': '#0061D5', 'auth_type': 'oauth'},
    {'id': 'supabase', 'name': 'Supabase', 'category': 'storage', 'description': 'Open-source backend with Postgres, auth, storage, and real-time APIs.', 'icon': '⚡', 'color': '#3ECF8E', 'auth_type': 'api_key'},
    {'id': 'neon', 'name': 'Neon', 'category': 'storage', 'description': 'Serverless Postgres for reliable and scalable applications.', 'icon': '🟢', 'color': '#00E599', 'auth_type': 'api_key'},

    # ── Social Media ──
    {'id': 'youtube', 'name': 'YouTube', 'category': 'social', 'description': 'Video-sharing platform for marketing, education, and entertainment.', 'icon': '▶️', 'color': '#FF0000', 'auth_type': 'oauth', 'provider': 'google'},
    {'id': 'facebook', 'name': 'Facebook', 'category': 'social', 'description': 'Social media and advertising platform. Pages only, not personal accounts.', 'icon': '📘', 'color': '#1877F2', 'auth_type': 'oauth'},
    {'id': 'linkedin', 'name': 'LinkedIn', 'category': 'social', 'description': 'Professional networking platform for job seekers and businesses.', 'icon': '💼', 'color': '#0A66C2', 'auth_type': 'oauth'},
    {'id': 'reddit', 'name': 'Reddit', 'category': 'social', 'description': 'Social news platform with user-driven communities.', 'icon': '🔴', 'color': '#FF4500', 'auth_type': 'oauth'},
    {'id': 'twitter', 'name': 'Twitter / X', 'category': 'social', 'description': 'Microblogging and social networking service.', 'icon': '🐦', 'color': '#1DA1F2', 'auth_type': 'oauth'},

    # ── AI & Search ──
    {'id': 'perplexity', 'name': 'Perplexity AI', 'category': 'ai', 'description': 'Conversational AI for generating human-like text responses.', 'icon': '🤖', 'color': '#20B8CD', 'auth_type': 'api_key'},
    {'id': 'elevenlabs', 'name': 'ElevenLabs', 'category': 'ai', 'description': 'Natural AI voices in any language for creators and businesses.', 'icon': '🎙️', 'color': '#000000', 'auth_type': 'api_key'},
    {'id': 'lmnt', 'name': 'LMNT', 'category': 'ai', 'description': 'Voice and audio manipulation with AI.', 'icon': '🔊', 'color': '#7C3AED', 'auth_type': 'api_key'},
    {'id': 'humanloop', 'name': 'Humanloop', 'category': 'ai', 'description': 'Build and refine AI applications with feedback loops.', 'icon': '🔄', 'color': '#5B47E0', 'auth_type': 'api_key'},
    {'id': 'mem0', 'name': 'Mem0', 'category': 'ai', 'description': 'Universal self-improving memory layer for LLM applications.', 'icon': '🧠', 'color': '#7C3AED', 'auth_type': 'api_key'},
    {'id': 'openai', 'name': 'OpenAI', 'category': 'ai', 'description': 'GPT models for text generation and analysis.', 'icon': '🤖', 'color': '#10A37F', 'auth_type': 'api_key'},
    {'id': 'anthropic', 'name': 'Anthropic', 'category': 'ai', 'description': 'Claude AI models for text generation and analysis.', 'icon': '🟤', 'color': '#D4A574', 'auth_type': 'api_key'},

    # ── Web Scraping & Data ──
    {'id': 'firecrawl', 'name': 'Firecrawl', 'category': 'data', 'description': 'Automated web crawling and data extraction at scale.', 'icon': '🔥', 'color': '#FF6B35', 'auth_type': 'api_key'},
    {'id': 'tavily', 'name': 'Tavily', 'category': 'data', 'description': 'Search and data retrieval for quick information access.', 'icon': '🔍', 'color': '#7C3AED', 'auth_type': 'api_key'},
    {'id': 'serpapi', 'name': 'SerpApi', 'category': 'data', 'description': 'Real-time structured search engine results API.', 'icon': '🔎', 'color': '#4285F4', 'auth_type': 'api_key'},
    {'id': 'bright-data', 'name': 'Bright Data', 'category': 'data', 'description': '#1 web data platform with SERP API and web unlocker.', 'icon': '☀️', 'color': '#FFD700', 'auth_type': 'api_key'},
    {'id': 'apify', 'name': 'Apify', 'category': 'data', 'description': 'Platform for web scraping and automation tools.', 'icon': '🕷️', 'color': '#1A1C23', 'auth_type': 'api_key'},
    {'id': 'exa', 'name': 'Exa', 'category': 'data', 'description': 'Data extraction and search for websites and APIs.', 'icon': '🔍', 'color': '#7C3AED', 'auth_type': 'api_key'},

    # ── DevOps & Monitoring ──
    {'id': 'pagerduty', 'name': 'PagerDuty', 'category': 'devops', 'description': 'Digital operations management with incident response.', 'icon': '🟢', 'color': '#06AC38', 'auth_type': 'api_key'},
    {'id': 'betterstack', 'name': 'Better Stack', 'category': 'devops', 'description': 'Monitoring, logging, and incident management.', 'icon': '📦', 'color': '#0F172A', 'auth_type': 'api_key'},

    # ── Scheduling ──
    {'id': 'calendly', 'name': 'Calendly', 'category': 'scheduling', 'description': 'Appointment scheduling with availability management.', 'icon': '📅', 'color': '#006BFF', 'auth_type': 'oauth'},
    {'id': 'cal', 'name': 'Cal.com', 'category': 'scheduling', 'description': 'Open-source meeting coordination with booking pages.', 'icon': '📅', 'color': '#29292E', 'auth_type': 'oauth'},
    {'id': 'google-calendar', 'name': 'Google Calendar', 'category': 'scheduling', 'description': 'Time management with scheduling and event reminders.', 'icon': '📆', 'color': '#4285F4', 'auth_type': 'oauth', 'provider': 'google'},

    # ── Forms & Surveys ──
    {'id': 'typeform', 'name': 'Typeform', 'category': 'forms', 'description': 'Beautiful forms and surveys with logic.', 'icon': '📝', 'color': '#262627', 'auth_type': 'api_key'},
    {'id': 'formsite', 'name': 'Formsite', 'category': 'forms', 'description': 'Online forms and surveys with integrations.', 'icon': '📋', 'color': '#4A90D9', 'auth_type': 'api_key'},
    {'id': 'formcarry', 'name': 'Formcarry', 'category': 'forms', 'description': 'Form API for collecting submissions without backend code.', 'icon': '📮', 'color': '#FF6B6B', 'auth_type': 'api_key'},
    {'id': 'canny', 'name': 'Canny', 'category': 'forms', 'description': 'Customer feedback management and feature prioritization.', 'icon': '🗳️', 'color': '#4B58FF', 'auth_type': 'oauth'},

    # ── Meeting & Transcription ──
    {'id': 'fireflies', 'name': 'Fireflies.ai', 'category': 'meetings', 'description': 'Transcribe, summarize, search, and analyze voice conversations.', 'icon': '🔥', 'color': '#FF6B35', 'auth_type': 'oauth'},
    {'id': 'meet', 'name': 'Google Meet', 'category': 'meetings', 'description': 'Secure video conferencing integrated with Google Workspace.', 'icon': '📹', 'color': '#00897B', 'auth_type': 'oauth', 'provider': 'google'},
    {'id': 'webex', 'name': 'Webex', 'category': 'meetings', 'description': 'Cisco-powered video conferencing and collaboration.', 'icon': '📹', 'color': '#00BCD4', 'auth_type': 'oauth'},
    {'id': 'recall-ai', 'name': 'Recall.ai', 'category': 'meetings', 'description': 'Unified API for meeting bots and conversation data.', 'icon': '🤖', 'color': '#7C3AED', 'auth_type': 'api_key'},

    # ── HR & Recruiting ──
    {'id': 'ashby', 'name': 'Ashby', 'category': 'hr', 'description': 'Applicant tracking system with data-driven hiring insights.', 'icon': '👥', 'color': '#0EA5E9', 'auth_type': 'oauth'},
    {'id': 'breathe-hr', 'name': 'Breathe HR', 'category': 'hr', 'description': 'Cloud-based HR software for SMEs.', 'icon': '💚', 'color': '#00B168', 'auth_type': 'api_key'},
    {'id': 'hackerrank', 'name': 'HackerRank', 'category': 'hr', 'description': 'Coding interviews and technical assessments.', 'icon': '💻', 'color': '#1BA94C', 'auth_type': 'api_key'},

    # ── Content Management ──
    {'id': 'contentful', 'name': 'Contentful', 'category': 'cms', 'description': 'Headless CMS with API-first content management.', 'icon': '📝', 'color': '#2FA4E6', 'auth_type': 'api_key'},
    {'id': 'agility-cms', 'name': 'Agility CMS', 'category': 'cms', 'description': 'Headless CMS for managing digital experiences.', 'icon': '📝', 'color': '#00B388', 'auth_type': 'api_key'},
]

CATEGORIES = [
    {'id': 'communication', 'label': 'Communication', 'icon': '💬'},
    {'id': 'crm', 'label': 'CRM & Sales', 'icon': '💼'},
    {'id': 'project', 'label': 'Project Management', 'icon': '📋'},
    {'id': 'development', 'label': 'Development', 'icon': '💻'},
    {'id': 'marketing', 'label': 'Marketing & SEO', 'icon': '📈'},
    {'id': 'ecommerce', 'label': 'E-commerce', 'icon': '🛍️'},
    {'id': 'finance', 'label': 'Finance & Accounting', 'icon': '💰'},
    {'id': 'data', 'label': 'Data & Analytics', 'icon': '📊'},
    {'id': 'support', 'label': 'Support & Helpdesk', 'icon': '🎧'},
    {'id': 'design', 'label': 'Design & Creative', 'icon': '🎨'},
    {'id': 'storage', 'label': 'Cloud Storage', 'icon': '☁️'},
    {'id': 'social', 'label': 'Social Media', 'icon': '📱'},
    {'id': 'ai', 'label': 'AI & Search', 'icon': '🤖'},
    {'id': 'devops', 'label': 'DevOps & Monitoring', 'icon': '🔧'},
    {'id': 'scheduling', 'label': 'Scheduling', 'icon': '📅'},
    {'id': 'forms', 'label': 'Forms & Surveys', 'icon': '📝'},
    {'id': 'meetings', 'label': 'Meetings & Transcription', 'icon': '📹'},
    {'id': 'hr', 'label': 'HR & Recruiting', 'icon': '👥'},
    {'id': 'cms', 'label': 'Content Management', 'icon': '📄'},
]

INTEGRATION_MAP = {i['id']: i for i in INTEGRATIONS}

# ═══════════════════════════════════════════════════════════════════════════════
# Availability gate — P0-7
# ═══════════════════════════════════════════════════════════════════════════════
# For the public beta, NO integration is production-ready: there is no OAuth
# flow, no credential validation, no token refresh, and no client code that
# actually talks to any provider. The previous /connect endpoint stored a fake
# "connected" row without doing anything, and the UI misled users into thinking
# they were connected. Until each integration has:
#   1. a real OAuth 2.0 flow (state + PKCE) OR validated API-key handshake,
#   2. encrypted-at-rest credential storage,
#   3. a working provider client,
#   4. a token-refresh + revocation worker,
# the integration is NOT available.
#
# `AVAILABLE_INTEGRATIONS` is the single source of truth. To ship a real
# integration in the future, add its id to this set (and remove the frontend
# "Coming Soon" pill). Every endpoint below enforces it — the UI cannot bypass
# by calling the API directly.
AVAILABLE_INTEGRATIONS: set = set()  # BETA: no integrations are live yet.


def _is_available(integration_id: str) -> bool:
    return integration_id in AVAILABLE_INTEGRATIONS


# ═══════════════════════════════════════════════════════════════════════════════
# API Routes
# ═══════════════════════════════════════════════════════════════════════════════

@router.get('/integrations')
async def list_integrations(category: str = '', search: str = '', user=Depends(get_current_user)):
    """List all available integrations with optional filtering."""
    items = INTEGRATIONS
    if category:
        items = [i for i in items if i['category'] == category]
    if search:
        s = search.lower()
        items = [i for i in items if s in i['name'].lower() or s in i['description'].lower()]

    # Get user's connected integrations
    user_conns = await db.user_integrations.find(
        {'user_id': user['id']}, {'_id': 0, 'integration_id': 1, 'status': 1, 'connected_at': 1}
    ).to_list(100)
    conn_map = {c['integration_id']: c for c in user_conns}

    result = []
    for i in items:
        conn = conn_map.get(i['id'])
        result.append({
            **i,
            'available': _is_available(i['id']),  # P0-7: honest availability flag
            'coming_soon': not _is_available(i['id']),
            'connected': bool(conn) and _is_available(i['id']),
            'status': (conn.get('status', 'disconnected') if conn else 'disconnected') if _is_available(i['id']) else 'coming_soon',
            'connected_at': conn.get('connected_at') if conn else None,
        })

    return {'integrations': result, 'categories': CATEGORIES, 'total': len(result)}


@router.get('/integrations/connected')
async def list_connected(user=Depends(get_current_user)):
    """List user's connected integrations."""
    cur = db.user_integrations.find(
        {'user_id': user['id'], 'status': 'connected'}, {'_id': 0}
    ).sort('connected_at', -1)
    items = [doc async for doc in cur]
    # Enrich with catalog info
    for item in items:
        info = INTEGRATION_MAP.get(item.get('integration_id', ''), {})
        item['name'] = info.get('name', item.get('integration_id', ''))
        item['icon'] = info.get('icon', '🔌')
        item['color'] = info.get('color', '#666')
    return {'connections': items}


class ConnectIn(BaseModel):
    integration_id: str
    credentials: Optional[Dict[str, str]] = None


@router.post('/integrations/connect')
async def connect_integration(payload: ConnectIn, user=Depends(get_current_user)):
    """Connect an integration.

    P0-7: For the public beta, NO integrations are enabled. The previous
    implementation blindly stored whatever credentials the client sent (or
    nothing at all) and marked the user "connected" — a facade. Until a real
    OAuth flow + encrypted credential store ships, every connect request is
    rejected at the backend so the API cannot be bypassed by hitting it
    directly (bypassing the frontend "Coming Soon" state).
    """
    integ = INTEGRATION_MAP.get(payload.integration_id)
    if not integ:
        raise HTTPException(status_code=404, detail='Integration not found')

    if not _is_available(payload.integration_id):
        # Log the attempt for waitlist analytics, but do NOT store any
        # credentials the client may have sent.
        try:
            await db.integration_waitlist.update_one(
                {'user_id': user['id'], 'integration_id': payload.integration_id},
                {'$set': {
                    'user_id': user['id'],
                    'integration_id': payload.integration_id,
                    'name': integ['name'],
                    'requested_at': datetime.now(timezone.utc).isoformat(),
                }},
                upsert=True,
            )
        except Exception:
            pass
        raise HTTPException(
            status_code=503,
            detail=f"{integ['name']} integration is coming soon. You've been added to the waitlist — we'll notify you when it's live.",
        )

    # Real integrations would fall through here with a validated OAuth flow.
    # None exist yet — this branch is intentionally unreachable in the beta.
    raise HTTPException(status_code=501, detail='Integration connect flow not implemented.')


class WaitlistIn(BaseModel):
    integration_id: str


@router.post('/integrations/waitlist')
async def integration_waitlist(payload: WaitlistIn, user=Depends(get_current_user)):
    """Explicit "Notify me" endpoint used by the Coming Soon UI."""
    integ = INTEGRATION_MAP.get(payload.integration_id)
    if not integ:
        raise HTTPException(status_code=404, detail='Integration not found')
    await db.integration_waitlist.update_one(
        {'user_id': user['id'], 'integration_id': payload.integration_id},
        {'$set': {
            'user_id': user['id'],
            'integration_id': payload.integration_id,
            'name': integ['name'],
            'requested_at': datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )
    return {'ok': True, 'waitlisted': True, 'integration_id': payload.integration_id}


@router.post('/integrations/disconnect')
async def disconnect_integration(integration_id: str, user=Depends(get_current_user)):
    """Disconnect an integration."""
    result = await db.user_integrations.delete_one({
        'user_id': user['id'],
        'integration_id': integration_id,
    })
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail='Connection not found')
    return {'ok': True, 'status': 'disconnected'}


@router.get('/integrations/{integration_id}')
async def get_integration(integration_id: str, user=Depends(get_current_user)):
    """Get details for a specific integration."""
    integ = INTEGRATION_MAP.get(integration_id)
    if not integ:
        raise HTTPException(status_code=404, detail='Integration not found')

    conn = await db.user_integrations.find_one({
        'user_id': user['id'],
        'integration_id': integration_id,
    }, {'_id': 0, 'credentials': 0})

    return {
        **integ,
        'connected': bool(conn),
        'status': conn.get('status', 'disconnected') if conn else 'disconnected',
        'connected_at': conn.get('connected_at') if conn else None,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Admin Routes
# ═══════════════════════════════════════════════════════════════════════════════

@router.get('/admin/integrations', dependencies=[Depends(get_current_admin)])
async def admin_list_integrations():
    """Admin: list all integrations with connection stats."""
    pipeline = [
        {'$group': {
            '_id': '$integration_id',
            'total_connections': {'$sum': 1},
            'active': {'$sum': {'$cond': [{'$eq': ['$status', 'connected']}, 1, 0]}},
        }},
        {'$sort': {'total_connections': -1}},
    ]
    stats = await db.user_integrations.aggregate(pipeline).to_list(200)
    stats_map = {s['_id']: s for s in stats}

    result = []
    for integ in INTEGRATIONS:
        s = stats_map.get(integ['id'], {'total_connections': 0, 'active': 0})
        result.append({**integ, 'total_connections': s['total_connections'], 'active_connections': s['active']})

    return {'integrations': result, 'total': len(result)}


@router.get('/admin/integrations/analytics', dependencies=[Depends(get_current_admin)])
async def admin_integration_analytics():
    """Admin: integration usage analytics."""
    pipeline = [
        {'$group': {
            '_id': '$integration_id',
            'total': {'$sum': 1},
            'active': {'$sum': {'$cond': [{'$eq': ['$status', 'connected']}, 1, 0]}},
            'users': {'$addToSet': '$user_id'},
        }},
        {'$project': {
            'integration_id': '$_id',
            'total': 1,
            'active': 1,
            'unique_users': {'$size': '$users'},
        }},
        {'$sort': {'total': -1}},
    ]
    results = await db.user_integrations.aggregate(pipeline).to_list(200)
    return {'analytics': results}
