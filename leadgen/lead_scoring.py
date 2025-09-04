#!/usr/bin/env python3
"""
Advanced Lead Scoring System for AI Chatbot Sales
Analyzes companies based on support intensity, growth signals, and implementation feasibility

Environment Variables:
- OPENAI_API_KEY: Your OpenAI API key
- OPENAI_MODEL: OpenAI model to use (default: gpt-4o-mini)
- LEAD_SCORING_MAX_TOKENS: Maximum tokens for responses (default: 1500)
- LEAD_SCORING_TEMPERATURE: Temperature for responses (default: 0.3)

Note: max_tokens and temperature are only used for models that support them
(GPT-4o, GPT-4, GPT-3.5 series). Other models will use OpenAI defaults.
"""

import asyncio
import logging
import re
import os
from typing import Dict, List, Optional, Tuple, Union, Callable, Awaitable, Type
from typing import get_origin, get_args
from dataclasses import dataclass
from datetime import datetime, timedelta
import openai
import json
import requests
from urllib.parse import urljoin, urlparse
import time
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from pydantic import BaseModel
from dotenv import load_dotenv

from .database import get_db_session
from app.models.leadgen_models import LeadgenCompany as Company
from .openai_enricher import OpenAICompanyEnricher

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Pydantic models for structured outputs

class SignalAnalysis(BaseModel):
    """Base model for signal analysis results"""
    score: int
    reasoning: str

class SupportInfrastructureAnalysis(SignalAnalysis):
    evidence: List[str]

class KBDepthAnalysis(SignalAnalysis):
    article_count_estimate: int
    categories: List[str]

class PostPurchaseAnalysis(SignalAnalysis):
    signals: List[str]
    tracking_providers: List[str]

class SupportToolingAnalysis(SignalAnalysis):
    tools_detected: List[str]
    has_ai_bot: bool
    chat_widgets: List[str]

class ReviewComplaintsAnalysis(SignalAnalysis):
    review_indicators: List[str]
    support_complaint_signals: List[str]

class SitemapDensityAnalysis(SignalAnalysis):
    estimated_page_count: int
    support_sections: List[str]

class FAQRichnessAnalysis(SignalAnalysis):
    faq_elements_count: int
    self_service_features: List[str]

class TrafficScaleAnalysis(SignalAnalysis):
    estimated_monthly_visits: int
    growth_indicators: List[str]

class CatalogSizeAnalysis(SignalAnalysis):
    ecommerce_detected: bool
    estimated_product_count: int
    platform_indicators: List[str]

class HiringVelocityAnalysis(SignalAnalysis):
    support_roles_count: int
    sales_roles_count: int
    velocity_indicators: List[str]

class HeadcountGrowthAnalysis(SignalAnalysis):
    growth_indicators: List[str]
    estimated_growth_rate: str

class RecentFundingAnalysis(SignalAnalysis):
    funding_indicators: List[str]
    funding_stage_estimate: str

class TechTeamSizeAnalysis(SignalAnalysis):
    estimated_tech_ratio: str
    tech_indicators: List[str]

class AIRolesAnalysis(SignalAnalysis):
    ai_roles_count: int
    ai_indicators: List[str]

class ExistingBotsAnalysis(SignalAnalysis):
    ai_bots_detected: List[str]
    automation_level: str

class ChatReadinessAnalysis(SignalAnalysis):
    readiness_indicators: List[str]
    implementation_ease: str

@dataclass
class LeadScore:
    """Container for all lead scoring signals and final score"""
    company_id: int
    company_name: str
    domain: str
    
    # Support Intensity Signals (0-100 points each)
    support_infrastructure_score: int = 0
    kb_depth_score: int = 0
    post_purchase_score: int = 0
    support_tooling_score: int = 0
    review_complaint_score: int = 0
    
    # Digital Presence Signals (0-100 points each)
    sitemap_density_score: int = 0
    faq_richness_score: int = 0
    traffic_scale_score: int = 0
    catalog_size_score: int = 0
    
    # Growth/Hiring Signals (0-100 points each)
    hiring_velocity_score: int = 0
    headcount_growth_score: int = 0
    recent_funding_score: int = 0
    
    # Implementation Feasibility (0-100 points each)
    small_tech_team_score: int = 0
    no_ai_roles_score: int = 0
    no_existing_bot_score: int = 0
    chat_ready_score: int = 0
    
    # Final composite scores
    support_intensity_total: int = 0
    digital_presence_total: int = 0
    growth_signals_total: int = 0
    implementation_feasibility_total: int = 0
    overall_score: int = 0
    
    # Detailed signal data for analysis
    signals_data: Dict = None
    
    def calculate_totals(self):
        """Calculate category totals and overall score"""
        self.support_intensity_total = (
            self.support_infrastructure_score + 
            self.kb_depth_score + 
            self.post_purchase_score + 
            self.support_tooling_score + 
            self.review_complaint_score
        )
        
        self.digital_presence_total = (
            self.sitemap_density_score + 
            self.faq_richness_score + 
            self.traffic_scale_score + 
            self.catalog_size_score
        )
        
        self.growth_signals_total = (
            self.hiring_velocity_score + 
            self.headcount_growth_score + 
            self.recent_funding_score
        )
        
        self.implementation_feasibility_total = (
            self.small_tech_team_score + 
            self.no_ai_roles_score + 
            self.no_existing_bot_score + 
            self.chat_ready_score
        )
        
        # Weighted overall score (support intensity = 40%, growth = 30%, implementation = 20%, digital = 10%)
        self.overall_score = int(
            (self.support_intensity_total * 0.4) + 
            (self.growth_signals_total * 0.3) + 
            (self.implementation_feasibility_total * 0.2) + 
            (self.digital_presence_total * 0.1)
        )

class LeadScoringEngine:
    """Advanced lead scoring engine using OpenAI for signal analysis"""
    
    def __init__(self):
        self.enricher = OpenAICompanyEnricher()
        self.openai_model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        # Log configuration
        logger.info(f"LeadScoringEngine initialized with model: {self.openai_model}")
        if self.openai_model.startswith(("gpt-4o", "gpt-4", "gpt-3.5")):
            max_tokens = os.getenv("LEAD_SCORING_MAX_TOKENS", "1500")
            temperature = os.getenv("LEAD_SCORING_TEMPERATURE", "0.3")
            logger.info(f"Model supports custom parameters: max_tokens={max_tokens}, temperature={temperature}")
        else:
            logger.info("Model uses OpenAI defaults for max_tokens and temperature")
    
    def get_configuration(self) -> Dict[str, str]:
        """Get current configuration for debugging"""
        config = {
            "openai_model": self.openai_model,
            "supports_custom_params": str(self.openai_model.startswith(("gpt-4o", "gpt-4", "gpt-3.5")))
        }
        if self.openai_model.startswith(("gpt-4o", "gpt-4", "gpt-3.5")):
            config["max_tokens"] = os.getenv("LEAD_SCORING_MAX_TOKENS", "1500")
            config["temperature"] = os.getenv("LEAD_SCORING_TEMPERATURE", "0.3")
        return config
    
    async def score_company(self, company_id: int, progress_callback: Optional[Callable[[str, int, int], Awaitable[None]]] = None) -> LeadScore:
        """Main function to score a company across all signals"""
        db = next(get_db_session())
        try:
            company = db.query(Company).filter(Company.id == company_id).first()
            if not company:
                raise ValueError(f"Company {company_id} not found")
            
            logger.info(f"Starting comprehensive lead scoring for {company.name} ({company.domain})")
            
            # Initialize lead score container
            score = LeadScore(
                company_id=company_id,
                company_name=company.name,
                domain=company.domain,
                signals_data={}
            )
            
            # Get base website content for analysis
            website_content = await self._fetch_website_content(company.domain)
            score.signals_data['website_content'] = website_content
            
            # Execute all phases with optional progress callback for UI updates
            phases: List[Tuple[str, Callable[[LeadScore], Awaitable[None]]]] = [
                ("support_infrastructure", self._analyze_support_infrastructure),
                ("kb_depth", self._analyze_kb_depth),
                ("post_purchase", self._analyze_post_purchase_signals),
                ("support_tooling", self._analyze_support_tooling),
                ("review_complaints", self._analyze_review_complaints),
                ("sitemap_density", self._analyze_sitemap_density),
                ("faq_richness", self._analyze_faq_richness),
                ("traffic_scale", self._analyze_traffic_scale),
                ("catalog_size", self._analyze_catalog_size),
                ("hiring_velocity", self._analyze_hiring_velocity),
                ("headcount_growth", self._analyze_headcount_growth),
                ("recent_funding", self._analyze_recent_funding),
                ("tech_team_size", self._analyze_tech_team_size),
                ("ai_roles", self._analyze_ai_roles),
                ("existing_bots", self._analyze_existing_bots),
                ("chat_readiness", self._analyze_chat_readiness),
            ]

            total_phases = len(phases)
            logger.info("Running lead scoring phases (%d phases)...", total_phases)
            for index, (phase_key, phase_func) in enumerate(phases):
                # Broadcast current phase if callback provided
                if progress_callback is not None:
                    try:
                        await progress_callback(phase_key, index, total_phases)
                    except Exception as cb_err:
                        logger.warning(f"Progress callback failed for phase {phase_key}: {cb_err}")

                logger.info(f"Executing phase {index+1}/{total_phases}: {phase_key}")
                await phase_func(score)
            
            # Calculate final scores
            score.calculate_totals()
            
            logger.info(f"Lead scoring complete for {company.name}. Overall score: {score.overall_score}/400")
            return score
            
        finally:
            db.close()
    
    async def _fetch_website_content(self, domain: str) -> Dict:
        """Fetch and analyze website content for signal detection"""
        if not domain:
            return {}
        
        try:
            url = f"https://{domain}"
            response = self.session.get(url, timeout=10, allow_redirects=True)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            # Extract JSON-LD blobs for schema.org analysis (FAQPage detection)
            json_ld_data = []
            try:
                for script in soup.find_all('script', type='application/ld+json'):
                    text = script.string or script.get_text() or ''
                    if not text:
                        continue
                    text = text.strip()
                    if len(text) > 5000:
                        text = text[:5000]
                    try:
                        json_ld_data.append(json.loads(text))
                    except Exception:
                        # Non-strict JSON or dynamic content – store raw for reference
                        json_ld_data.append({"raw": text[:1000]})
            except Exception:
                pass
            
            return {
                'html': response.text[:50000],  # Limit to prevent token overflow
                'title': soup.title.string if soup.title else '',
                'meta_description': soup.find('meta', attrs={'name': 'description'})['content'] if soup.find('meta', attrs={'name': 'description'}) else '',
                'links': [a.get('href') for a in soup.find_all('a', href=True)][:100],
                'text_content': soup.get_text()[:10000],
                'scripts': [script.get('src') for script in soup.find_all('script', src=True)][:50],
                'json_ld': json_ld_data
            }
        except Exception as e:
            logger.warning(f"Failed to fetch website content for {domain}: {e}")
            return {}

    # SUPPORT INTENSITY SIGNAL ANALYZERS
    
    async def _analyze_support_infrastructure(self, score: LeadScore):
        """Analyze presence of support infrastructure (help centers, KB systems)"""
        try:
            website = score.signals_data.get('website_content', {})
            html_sample = website.get('html', '')[:3000]
            links = website.get('links', [])
            json_ld = website.get('json_ld', [])
            
            # Heuristic detection of support/FAQ resources
            support_keywords = ['help', 'support', 'faq', 'kb', 'docs', 'knowledge', 'patient-info', 'patient-info-faq', 'resources', 'portal']
            support_links = []
            for link in links:
                low = (link or '').lower()
                if any(kw in low for kw in support_keywords):
                    if low.startswith('/'):
                        support_links.append(f"https://{score.domain}{link}")
                    elif low.startswith('http'):
                        support_links.append(link)
            html_has_faq = bool(re.search(r"\bfaq\b|frequently\s+asked\s+questions", html_sample, re.IGNORECASE))
            jsonld_has_faq = False
            try:
                for blob in json_ld or []:
                    if isinstance(blob, dict):
                        at = blob.get('@type')
                        # @type may be a list or string
                        if isinstance(at, str) and at.lower() == 'faqpage':
                            jsonld_has_faq = True
                            break
                        if isinstance(at, list) and any(isinstance(x, str) and x.lower() == 'faqpage' for x in at):
                            jsonld_has_faq = True
                            break
            except Exception:
                pass
            pre_detected_evidence = []
            if support_links:
                pre_detected_evidence.append(f"Detected potential support links: {support_links[:5]}")
            if html_has_faq:
                pre_detected_evidence.append("Detected 'FAQ' mentions in page HTML")
            if jsonld_has_faq:
                pre_detected_evidence.append("Detected schema.org FAQPage in JSON-LD")
            
            prompt = f"""
            Analyze this company's support infrastructure based on their website.
            Company: {score.company_name}
            Domain: {score.domain}
            Website content: {html_sample}
            Candidate support links found: {support_links}
            Pre-detected indicators: {pre_detected_evidence}
            
            Look for:
            1. Hosted help centers (help.|support.|kb.|faq. subdomains)
            2. Third-party knowledge base systems:
               - zendesk.com, intercom.help, helpscoutdocs.com, freshdesk.com
               - gorgias.help, desk.zoho.com, kayako.com, docsify, document360
            3. Support page links or sections
            4. Help/FAQ/Knowledge Base mentions
            
            Score from 0-100 where:
            - 0-20: No visible support infrastructure
            - 21-40: Basic FAQ or help page
            - 41-60: Dedicated support section
            - 61-80: Comprehensive help center or third-party KB
            - 81-100: Multiple support channels with professional KB system
            """
            
            result = await self._call_openai_structured(prompt, SupportInfrastructureAnalysis)
            # Apply heuristic minimums if we detected FAQ/support resources
            adjusted_score = result.score
            heuristic_notes = []
            if html_has_faq or support_links:
                adjusted_score = max(adjusted_score, 40)
                heuristic_notes.append('Raised to at least 40 due to detected FAQ/support links')
            if jsonld_has_faq:
                adjusted_score = max(adjusted_score, 60)
                heuristic_notes.append('Raised to at least 60 due to schema.org FAQPage')
            
            score.support_infrastructure_score = min(100, max(0, adjusted_score))
            support_payload = result.model_dump()
            if pre_detected_evidence:
                support_payload['pre_detected_evidence'] = pre_detected_evidence
            if heuristic_notes:
                support_payload['heuristic_adjustments'] = heuristic_notes
            score.signals_data['support_infrastructure'] = support_payload
            
            logger.info(f"Support infrastructure score: {score.support_infrastructure_score}/100")
            
        except Exception as e:
            logger.error(f"Error analyzing support infrastructure: {e}")
            score.support_infrastructure_score = 0
    
    async def _analyze_kb_depth(self, score: LeadScore):
        """Analyze knowledge base depth and content richness"""
        try:
            # Try to find and analyze help/support pages
            help_urls = []
            base_links = score.signals_data.get('website_content', {}).get('links', [])
            
            for link in base_links:
                if any(keyword in link.lower() for keyword in ['help', 'support', 'faq', 'kb', 'docs']):
                    if link.startswith('/'):
                        help_urls.append(f"https://{score.domain}{link}")
                    elif link.startswith('http'):
                        help_urls.append(link)
            
            help_content = ""
            for url in help_urls[:3]:  # Analyze up to 3 help pages
                try:
                    response = self.session.get(url, timeout=10)
                    if response.status_code == 200:
                        help_soup = BeautifulSoup(response.content, 'html.parser')
                        help_content += help_soup.get_text()[:2000]  # Limit content
                except:
                    continue
            
            prompt = f"""
            Analyze the knowledge base depth for this company's support system.
            Company: {score.company_name}
            Help content found: {help_content}
            
            Evaluate:
            1. Number of help articles/FAQs (estimate from content structure)
            2. Content categories and organization
            3. Freshness indicators (recent updates, current information)
            4. Depth of technical documentation
            5. Self-service capabilities
            
            Score from 0-100 where:
            - 0-20: No KB or minimal FAQs (<10 items)
            - 21-40: Basic FAQ section (10-25 items)
            - 41-60: Structured help center (25-50 articles)
            - 61-80: Comprehensive KB (50+ articles, multiple categories)
            - 81-100: Extensive self-service KB (100+ articles, searchable, regularly updated)
            """
            
            result = await self._call_openai_structured(prompt, KBDepthAnalysis)
            
            score.kb_depth_score = min(100, max(0, result.score))
            score.signals_data['kb_depth'] = result.model_dump()
            
            logger.info(f"KB depth score: {score.kb_depth_score}/100")
            
        except Exception as e:
            logger.error(f"Error analyzing KB depth: {e}")
            score.kb_depth_score = 0
    
    async def _analyze_post_purchase_signals(self, score: LeadScore):
        """Analyze post-purchase support signals that indicate support load"""
        try:
            website_content = score.signals_data.get('website_content', {})
            
            prompt = f"""
            Analyze post-purchase support signals that indicate customer service load.
            Company: {score.company_name}
            Website content: {website_content.get('html', '')[:3000]}
            Links found: {website_content.get('links', [])[:50]}
            
            Look for indicators of post-purchase support needs:
            1. Returns/exchanges pages or policies
            2. Warranty information and claims
            3. Shipping/delivery support
            4. Order tracking systems
            5. Appointment/booking changes
            6. Product registration
            7. Technical support sections
            8. Account management features
            
            Also detect order tracking providers:
            - AfterShip, Route, Narvar, Shippo, EasyPost
            - Happy Returns, Loop Returns
            - Custom tracking implementations
            
            Score from 0-100 where:
            - 0-20: Service/digital product with minimal post-purchase needs
            - 21-40: Some post-purchase pages but limited complexity
            - 41-60: Multiple post-purchase touchpoints
            - 61-80: Complex fulfillment with tracking and returns
            - 81-100: High-touch post-purchase experience with multiple providers
            """
            
            result = await self._call_openai_structured(prompt, PostPurchaseAnalysis)
            
            score.post_purchase_score = min(100, max(0, result.score))
            score.signals_data['post_purchase'] = result.model_dump()
            
            logger.info(f"Post-purchase signals score: {score.post_purchase_score}/100")
            
        except Exception as e:
            logger.error(f"Error analyzing post-purchase signals: {e}")
            score.post_purchase_score = 0
    
    async def _analyze_support_tooling(self, score: LeadScore):
        """Detect support tooling signatures and sophistication"""
        try:
            website_content = score.signals_data.get('website_content', {})
            scripts = website_content.get('scripts', [])
            html_content = website_content.get('html', '')
            
            prompt = f"""
            Detect support tooling and customer service platforms from website signatures.
            Company: {score.company_name}
            Scripts loaded: {scripts}
            HTML content sample: {html_content[:2000]}
            
            Look for signatures of support tools:
            1. Major platforms: Gorgias, Zendesk, Intercom, Kustomer, Freshdesk
            2. LiveChat systems: LiveChat, Drift, Crisp, Olark, Tawk.to
            3. Helpdesk widgets and chat bubbles
            4. Support ticket systems
            5. Customer portal integrations
            
            Pay special attention to:
            - Absence of AI/bot add-ons (which would reduce our value)
            - Traditional support tools without AI enhancement
            - Chat widgets that could be replaced
            
            Score from 0-100 where:
            - 0-20: No detectable support tooling
            - 21-40: Basic contact forms or email support
            - 41-60: Traditional helpdesk or chat tool
            - 61-80: Professional support platform without AI
            - 81-100: Sophisticated support stack but no AI/automation
            """
            
            result = await self._call_openai_structured(prompt, SupportToolingAnalysis)
            
            score.support_tooling_score = min(100, max(0, result.score))
            score.signals_data['support_tooling'] = result.model_dump()
            
            logger.info(f"Support tooling score: {score.support_tooling_score}/100")
            
        except Exception as e:
            logger.error(f"Error analyzing support tooling: {e}")
            score.support_tooling_score = 0
    
    async def _analyze_review_complaints(self, score: LeadScore):
        """Analyze review volume and support-related complaints"""
        try:
            prompt = f"""
            Research and analyze customer review patterns for support-related pain points.
            Company: {score.company_name}
            Domain: {score.domain}
            
            Analyze potential review sources and complaint patterns:
            1. Trustpilot, BBB, Google Reviews presence
            2. Common complaints about response time
            3. Support-related negative feedback
            4. Volume of customer service mentions
            5. Response time complaints
            6. Satisfaction with current support
            
            This is a signal that they need better support automation.
            
            Score from 0-100 where:
            - 0-20: No significant review presence or support complaints
            - 21-40: Some reviews but minimal support issues mentioned
            - 41-60: Moderate review volume with occasional support complaints
            - 61-80: High review volume with frequent support/response time issues
            - 81-100: Significant complaint volume about slow/poor support
            
            Note: This is inferential analysis based on company type and typical patterns.
            """
            
            result = await self._call_openai_structured(prompt, ReviewComplaintsAnalysis)
            
            score.review_complaint_score = min(100, max(0, result.score))
            score.signals_data['review_complaints'] = result.model_dump()
            
            logger.info(f"Review complaints score: {score.review_complaint_score}/100")
            
        except Exception as e:
            logger.error(f"Error analyzing review complaints: {e}")
            score.review_complaint_score = 0

    # DIGITAL PRESENCE SIGNAL ANALYZERS
    
    async def _analyze_sitemap_density(self, score: LeadScore):
        """Analyze sitemap density and support page presence"""
        try:
            # Try to fetch sitemap
            sitemap_urls = [
                f"https://{score.domain}/sitemap.xml",
                f"https://{score.domain}/sitemap_index.xml",
                f"https://{score.domain}/robots.txt"
            ]
            
            sitemap_data = {}
            for url in sitemap_urls:
                try:
                    response = self.session.get(url, timeout=10)
                    if response.status_code == 200:
                        sitemap_data[url] = response.text[:5000]  # Limit content
                except:
                    continue
            
            website_content = score.signals_data.get('website_content', {})
            links = website_content.get('links', [])
            
            prompt = f"""
            Analyze website density and support page presence.
            Company: {score.company_name}
            Sitemap data: {sitemap_data}
            Links found: {links[:100]}
            
            Evaluate:
            1. Total estimated page count (from sitemap or link analysis)
            2. Presence of dedicated support sections: /help, /support, /faq, /kb, /docs
            3. Website complexity and content richness
            4. Navigation structure depth
            5. Documentation organization
            
            Score from 0-100 where:
            - 0-20: Simple site <50 pages, no dedicated support
            - 21-40: Medium site 50-200 pages, basic support
            - 41-60: Large site 200-500 pages, some support sections
            - 61-80: Complex site 500+ pages, dedicated support areas
            - 81-100: Enterprise site 1000+ pages, comprehensive support structure
            """
            
            result = await self._call_openai_structured(prompt, SitemapDensityAnalysis)
            
            score.sitemap_density_score = min(100, max(0, result.score))
            score.signals_data['sitemap_density'] = result.model_dump()
            
            logger.info(f"Sitemap density score: {score.sitemap_density_score}/100")
            
        except Exception as e:
            logger.error(f"Error analyzing sitemap density: {e}")
            score.sitemap_density_score = 0
    
    async def _analyze_faq_richness(self, score: LeadScore):
        """Analyze FAQ richness and self-service content"""
        try:
            website_content = score.signals_data.get('website_content', {})
            html_content = website_content.get('html', '')
            links = website_content.get('links', []) or []

            # Build candidate FAQ/support URLs
            candidate_slugs = [
                '/faq', '/faqs', '/patient-info-faq', '/patient-info', '/help', '/support',
                '/resources', '/knowledge-base', '/kb', '/customer-support'
            ]
            candidate_urls = []
            for link in links[:100]:
                low = (link or '').lower()
                if any(kw in low for kw in ['faq', 'patient-info', 'help', 'support', 'knowledge', 'resource']):
                    if low.startswith('/'):
                        candidate_urls.append(f"https://{score.domain}{link}")
                    elif low.startswith('http'):
                        candidate_urls.append(link)
            candidate_urls.extend([f"https://{score.domain}{slug}" for slug in candidate_slugs])
            # Deduplicate
            seen = set()
            deduped = []
            for u in candidate_urls:
                if u not in seen:
                    seen.add(u)
                    deduped.append(u)
            candidate_urls = deduped[:5]

            # Fetch and analyze candidate FAQ pages
            detected_features: List[str] = []
            faq_items_count = 0
            jsonld_faq_detected = False
            fetched_pages: List[Tuple[str, str]] = []  # (url, text)
            for url in candidate_urls:
                try:
                    resp = self.session.get(url, timeout=10)
                    if resp.status_code == 200:
                        txt = resp.text[:20000]
                        fetched_pages.append((url, txt))
                        soup = BeautifulSoup(resp.content, 'html.parser')
                        # JSON-LD FAQPage
                        for script in soup.find_all('script', type='application/ld+json'):
                            try:
                                blob = json.loads(script.get_text() or '{}')
                                at = blob.get('@type')
                                if (isinstance(at, str) and at.lower() == 'faqpage') or \
                                   (isinstance(at, list) and any(isinstance(x, str) and x.lower() == 'faqpage' for x in at)):
                                    jsonld_faq_detected = True
                                    if isinstance(blob.get('mainEntity'), list):
                                        faq_items_count += len(blob['mainEntity'])
                            except Exception:
                                pass
                        # Heuristic count of questions/answers in DOM
                        text = soup.get_text(" ")
                        q_matches = len(re.findall(r'\b(question|faq|q:)\b', text, re.IGNORECASE))
                        a_matches = len(re.findall(r'\b(answer|a:)\b', text, re.IGNORECASE))
                        faq_items_count += max(q_matches, a_matches) // 2
                        # Detect accordions/expanders
                        if soup.select('.accordion, .accordion-item, details, [aria-expanded]'):
                            detected_features.append('Accordion/Expandable FAQ')
                        # Detect search bar in help context
                        if soup.find('input', attrs={'type': 'search'}) or re.search(r'help\s+search|faq\s+search', text, re.IGNORECASE):
                            detected_features.append('Help Search')
                        # Detect self-service items
                        for phrase, label in [
                            ('live chat', 'Live Chat'), ('chat', 'Chat Widget'), ('patient portal', 'Patient Portal'),
                            ('schedule online', 'Online Scheduling'), ('upload rx', 'Upload RX'), ('portal login', 'Portal Login'),
                            ('knowledge base', 'Knowledge Base'), ('resources', 'Resources Section')
                        ]:
                            if re.search(phrase, text, re.IGNORECASE):
                                detected_features.append(label)
                except Exception:
                    continue

            # Heuristic score floors
            heuristic_floor = 0
            if faq_items_count >= 5:
                heuristic_floor = max(heuristic_floor, 40)
            if faq_items_count >= 10:
                heuristic_floor = max(heuristic_floor, 60)
            if faq_items_count >= 25:
                heuristic_floor = max(heuristic_floor, 80)
            if jsonld_faq_detected:
                heuristic_floor = max(heuristic_floor, 60)

            prompt = f"""
            Analyze FAQ and self-service content richness.
            Company: {score.company_name}
            Homepage HTML: {html_content[:2000]}
            Candidate FAQ URLs: {candidate_urls}
            Sample FAQ Page Snippets: {[p[1][:800] for p in fetched_pages[:2]]}
            Pre-detected counts: faq_items_count={faq_items_count}, jsonld_faq_detected={jsonld_faq_detected}, self_service_features={list(set(detected_features))}
            
            Look for:
            1. FAQ accordions and expandable sections
            2. Structured FAQs (schema.org FAQPage)
            3. Help text and tooltips
            4. Self-service widgets (live chat, portal, scheduling)
            5. Search for help content
            6. FAQ organization and categorization
            
            Score from 0-100 where:
            - 0-20: No FAQs or minimal help text
            - 21-40: Basic FAQ section with <10 questions
            - 41-60: Structured FAQs with 10-25 questions
            - 61-80: Rich FAQ system with categories and search
            - 81-100: Comprehensive self-service with interactive help
            """

            llm = await self._call_openai_structured(prompt, FAQRichnessAnalysis)

            # Merge heuristic detections with LLM output
            merged_count = max(getattr(llm, 'faq_elements_count', 0) or 0, faq_items_count)
            merged_features = sorted(list(set((getattr(llm, 'self_service_features', []) or []) + list(set(detected_features)))))
            final_score = max(llm.score or 0, heuristic_floor)

            score.faq_richness_score = min(100, max(0, final_score))
            payload = {
                'score': score.faq_richness_score,
                'faq_elements_count': merged_count,
                'self_service_features': merged_features,
                'reasoning': getattr(llm, 'reasoning', '') or 'Heuristic and LLM-based analysis',
                'detected_faq_urls': candidate_urls,
                'jsonld_faq_detected': jsonld_faq_detected,
                'heuristic_floor_applied': heuristic_floor,
            }
            score.signals_data['faq_richness'] = payload
            
            logger.info(f"FAQ richness score: {score.faq_richness_score}/100")
            
        except Exception as e:
            logger.error(f"Error analyzing FAQ richness: {e}")
            score.faq_richness_score = 0
    
    async def _analyze_traffic_scale(self, score: LeadScore):
        """Estimate traffic scale and growth patterns"""
        try:
            prompt = f"""
            Estimate traffic scale and growth potential for this company.
            Company: {score.company_name}
            Domain: {score.domain}
            Industry: Based on website analysis
            
            Provide educated estimates for:
            1. Monthly website traffic scale
            2. Growth trajectory indicators
            3. Digital marketing sophistication
            4. Content freshness and update frequency
            5. SEO optimization level
            6. Social media presence indicators
            
            Consider company size, industry, and digital sophistication.
            
            Score from 0-100 where:
            - 0-20: Very low traffic <10K/month, limited growth
            - 21-40: Low traffic 10K-50K/month, slow growth
            - 41-60: Medium traffic 50K-200K/month, steady growth
            - 61-80: High traffic 200K-500K/month, strong growth
            - 81-100: Very high traffic >500K/month, rapid growth
            """
            
            result = await self._call_openai_structured(prompt, TrafficScaleAnalysis)
            
            score.traffic_scale_score = min(100, max(0, result.score))
            score.signals_data['traffic_scale'] = result.model_dump()
            
            logger.info(f"Traffic scale score: {score.traffic_scale_score}/100")
            
        except Exception as e:
            logger.error(f"Error analyzing traffic scale: {e}")
            score.traffic_scale_score = 0
    
    async def _analyze_catalog_size(self, score: LeadScore):
        """Analyze product catalog size for e-commerce companies"""
        try:
            website_content = score.signals_data.get('website_content', {})
            links = website_content.get('links', [])
            html_content = website_content.get('html', '')
            
            prompt = f"""
            Analyze product catalog size and e-commerce complexity.
            Company: {score.company_name}
            Website links: {links[:50]}
            HTML content: {html_content[:2000]}
            
            Evaluate:
            1. E-commerce indicators (shopping cart, product pages, checkout)
            2. Product catalog depth (categories, subcategories)
            3. Inventory management complexity
            4. Product variation handling (sizes, colors, options)
            5. B2B vs B2C selling patterns
            
            Look for:
            - Product detail page patterns
            - Category navigation
            - Shopping cart functionality
            - E-commerce platform signatures (Shopify, WooCommerce, Magento)
            
            Score from 0-100 where:
            - 0-20: No e-commerce or service-only business
            - 21-40: Small catalog <50 products or simple service offerings
            - 41-60: Medium catalog 50-500 products
            - 61-80: Large catalog 500-5000 products
            - 81-100: Massive catalog >5000 products or complex B2B offerings
            """
            
            result = await self._call_openai_structured(prompt, CatalogSizeAnalysis)
            
            score.catalog_size_score = min(100, max(0, result.score))
            score.signals_data['catalog_size'] = result.model_dump()
            
            logger.info(f"Catalog size score: {score.catalog_size_score}/100")
            
        except Exception as e:
            logger.error(f"Error analyzing catalog size: {e}")
            score.catalog_size_score = 0

    # GROWTH/HIRING SIGNAL ANALYZERS
    
    async def _analyze_hiring_velocity(self, score: LeadScore):
        """Analyze hiring velocity in support and sales roles"""
        try:
            # Get company from database to check for job postings
            db = next(get_db_session())
            try:
                company = db.query(Company).filter(Company.id == score.company_id).first()
                current_support_roles = company.support_roles if hasattr(company, 'support_roles') else 0
                current_sales_roles = company.sales_roles if hasattr(company, 'sales_roles') else 0
                total_roles = company.total_roles if hasattr(company, 'total_roles') else 0
            finally:
                db.close()
            
            prompt = f"""
            Analyze hiring velocity and growth signals for customer-facing roles.
            Company: {score.company_name}
            Current support roles: {current_support_roles}
            Current sales roles: {current_sales_roles}
            Total open roles: {total_roles}
            
            Evaluate hiring velocity indicators:
            1. Support/Customer Success role openings
            2. Sales/AE/SDR role openings  
            3. Customer-facing role growth rate
            4. Urgency indicators in job postings
            5. Multiple similar roles posted (scaling signal)
            6. Recent hiring announcements
            
            Strong hiring velocity in support/sales indicates:
            - Growing customer base
            - Support load increasing
            - Need for automation/efficiency
            
            Score from 0-100 where:
            - 0-20: No customer-facing roles, stable team
            - 21-40: 1-2 support/sales roles, slow hiring
            - 41-60: 3-5 support/sales roles, moderate growth
            - 61-80: 6-10 support/sales roles, rapid expansion
            - 81-100: >10 support/sales roles, aggressive scaling
            """
            
            result = await self._call_openai_structured(prompt, HiringVelocityAnalysis)
            
            score.hiring_velocity_score = min(100, max(0, result.score))
            score.signals_data['hiring_velocity'] = result.model_dump()
            
            logger.info(f"Hiring velocity score: {score.hiring_velocity_score}/100")
            
        except Exception as e:
            logger.error(f"Error analyzing hiring velocity: {e}")
            score.hiring_velocity_score = 0
    
    async def _analyze_headcount_growth(self, score: LeadScore):
        """Analyze overall headcount growth patterns"""
        try:
            prompt = f"""
            Analyze headcount growth patterns and expansion indicators.
            Company: {score.company_name}
            Domain: {score.domain}
            
            Look for growth indicators:
            1. Total headcount estimates and growth rate
            2. New office openings or expansions
            3. Team page growth over time
            4. LinkedIn employee count trends
            5. Press releases about hiring
            6. "We're hiring" messaging prominence
            7. Referral program indicators
            
            Growing companies need better support automation as they scale.
            
            Score from 0-100 where:
            - 0-20: Stable/declining headcount, no growth signals
            - 21-40: Slow growth <20% annually
            - 41-60: Moderate growth 20-50% annually
            - 61-80: High growth 50-100% annually  
            - 81-100: Hypergrowth >100% annually or major expansion
            """
            
            result = await self._call_openai_structured(prompt, HeadcountGrowthAnalysis)
            
            score.headcount_growth_score = min(100, max(0, result.score))
            score.signals_data['headcount_growth'] = result.model_dump()
            
            logger.info(f"Headcount growth score: {score.headcount_growth_score}/100")
            
        except Exception as e:
            logger.error(f"Error analyzing headcount growth: {e}")
            score.headcount_growth_score = 0
    
    async def _analyze_recent_funding(self, score: LeadScore):
        """Analyze recent funding and expansion signals"""
        try:
            prompt = f"""
            Research recent funding and expansion signals.
            Company: {score.company_name}
            Domain: {score.domain}
            
            Look for funding and expansion indicators:
            1. Recent funding announcements (last 12-18 months)
            2. Series A, B, C funding stages
            3. Expansion announcements
            4. New product launches
            5. Partnership announcements
            6. Press coverage about growth
            7. Investor backing signals
            8. "Backed by" or investor mentions
            
            Recent funding often leads to rapid scaling and support needs.
            
            Score from 0-100 where:
            - 0-20: No funding signals, bootstrap/mature company
            - 21-40: Some growth signals but no recent funding
            - 41-60: Moderate funding or growth announcements
            - 61-80: Significant recent funding or major expansion
            - 81-100: Major funding round or IPO/acquisition within 18 months
            """
            
            result = await self._call_openai_structured(prompt, RecentFundingAnalysis)
            
            score.recent_funding_score = min(100, max(0, result.score))
            score.signals_data['recent_funding'] = result.model_dump()
            
            logger.info(f"Recent funding score: {score.recent_funding_score}/100")
            
        except Exception as e:
            logger.error(f"Error analyzing recent funding: {e}")
            score.recent_funding_score = 0

    # IMPLEMENTATION FEASIBILITY ANALYZERS
    
    async def _analyze_tech_team_size(self, score: LeadScore):
        """Analyze tech team size relative to overall company"""
        try:
            # Get current job postings from database
            db = next(get_db_session())
            try:
                company = db.query(Company).filter(Company.id == score.company_id).first()
                total_roles = company.total_roles if hasattr(company, 'total_roles') else 0
                ai_roles = company.ai_roles if hasattr(company, 'ai_roles') else 0
                employee_count = company.employee_count or 50
            finally:
                db.close()
            
            prompt = f"""
            Analyze tech team size and engineering ratio.
            Company: {score.company_name}
            Employee count: {employee_count}
            Total open roles: {total_roles}
            AI/ML roles: {ai_roles}
            
            Evaluate technical capacity:
            1. Engineering headcount ratio (Engineering / Total employees)
            2. Technical role postings vs non-technical
            3. CTO/technical leadership presence
            4. Engineering blog or technical content
            5. Developer-focused features or APIs
            6. Technical complexity indicators
            
            Smaller tech teams are better prospects because:
            - Less likely to build custom AI solutions
            - More receptive to third-party tools
            - Need efficiency solutions
            
            Score from 0-100 where:
            - 0-20: Large tech team >20% of company, heavy engineering focus
            - 21-40: Medium tech team 15-20%, moderate technical capacity
            - 41-60: Small tech team 10-15%, limited technical resources
            - 61-80: Very small tech team 5-10%, minimal engineering
            - 81-100: Tiny/no tech team <5%, non-technical company
            """
            
            result = await self._call_openai_structured(prompt, TechTeamSizeAnalysis)
            
            score.small_tech_team_score = min(100, max(0, result.score))
            score.signals_data['tech_team_size'] = result.model_dump()
            
            logger.info(f"Small tech team score: {score.small_tech_team_score}/100")
            
        except Exception as e:
            logger.error(f"Error analyzing tech team size: {e}")
            score.small_tech_team_score = 0
    
    async def _analyze_ai_roles(self, score: LeadScore):
        """Analyze presence of AI/ML roles and capabilities"""
        try:
            # Get AI role count from database
            db = next(get_db_session())
            try:
                company = db.query(Company).filter(Company.id == score.company_id).first()
                ai_roles = company.ai_roles if hasattr(company, 'ai_roles') else 0
            finally:
                db.close()
            
            prompt = f"""
            Analyze AI/ML capabilities and internal AI development.
            Company: {score.company_name}
            AI/ML job openings: {ai_roles}
            
            Look for AI/ML indicators:
            1. AI/ML engineer job postings
            2. Data scientist roles
            3. LLM/AI-specific positions
            4. Machine learning mentions
            5. AI product features
            6. Technical blog posts about AI
            7. AI-powered product announcements
            8. Research publications or patents
            
            Companies with no AI roles are better prospects because:
            - They won't build competing solutions
            - They need external AI capabilities
            - They're open to third-party tools
            
            Score from 0-100 where:
            - 0-20: Heavy AI focus, multiple AI roles, AI product company
            - 21-40: Some AI capabilities, 1-2 AI roles
            - 41-60: Limited AI focus, exploring AI applications
            - 61-80: Minimal AI activity, no dedicated AI roles
            - 81-100: No AI roles, no AI mentions, perfect prospect
            """
            
            result = await self._call_openai_structured(prompt, AIRolesAnalysis)
            
            score.no_ai_roles_score = min(100, max(0, result.score))
            score.signals_data['ai_roles'] = result.model_dump()
            
            logger.info(f"No AI roles score: {score.no_ai_roles_score}/100")
            
        except Exception as e:
            logger.error(f"Error analyzing AI roles: {e}")
            score.no_ai_roles_score = 0
    
    async def _analyze_existing_bots(self, score: LeadScore):
        """Detect existing AI chatbots and automation"""
        try:
            website_content = score.signals_data.get('website_content', {})
            scripts = website_content.get('scripts', [])
            html_content = website_content.get('html', '')
            
            prompt = f"""
            Detect existing AI chatbots and automation systems.
            Company: {score.company_name}
            Scripts: {scripts}
            HTML: {html_content[:3000]}
            
            Look for AI bot signatures:
            1. Advanced AI platforms: Ada, Forethought, Ultimate.ai, Khoros
            2. AI-enhanced tools: Intercom Fin, Zendesk Advanced Bots
            3. Custom AI implementations
            4. Bot framework indicators
            5. Natural language processing features
            6. Automated response systems
            7. AI chat widget signatures
            8. Machine learning-powered features
            
            Companies without existing AI bots are better prospects.
            
            Score from 0-100 where:
            - 0-20: Advanced AI bot detected, sophisticated automation
            - 21-40: Basic AI features or simple bot implementation
            - 41-60: Some automation but not AI-powered
            - 61-80: Traditional chat but no AI detected
            - 81-100: No AI bots, traditional support only
            """
            
            result = await self._call_openai_structured(prompt, ExistingBotsAnalysis)
            
            score.no_existing_bot_score = min(100, max(0, result.score))
            score.signals_data['existing_bots'] = result.model_dump()
            
            logger.info(f"No existing bot score: {score.no_existing_bot_score}/100")
            
        except Exception as e:
            logger.error(f"Error analyzing existing bots: {e}")
            score.no_existing_bot_score = 0
    
    async def _analyze_chat_readiness(self, score: LeadScore):
        """Analyze technical readiness for chat widget implementation"""
        try:
            website_content = score.signals_data.get('website_content', {})
            scripts = website_content.get('scripts', [])
            html_content = website_content.get('html', '')
            
            prompt = f"""
            Analyze technical readiness for chat widget implementation.
            Company: {score.company_name}
            Scripts: {scripts}
            HTML: {html_content[:2000]}
            
            Look for implementation readiness indicators:
            1. Google Tag Manager (GTM) installation
            2. Existing chat widgets (easy to replace)
            3. JavaScript framework usage
            4. Widget/plugin architecture
            5. Tag management systems
            6. E-commerce platform compatibility
            7. CMS flexibility (WordPress, etc.)
            8. Third-party integration patterns
            
            Easy implementation means higher conversion probability.
            
            Score from 0-100 where:
            - 0-20: Static site, no JS, difficult implementation
            - 21-40: Basic site with limited JS capabilities
            - 41-60: Moderate JS usage, some third-party tools
            - 61-80: Good technical setup, GTM or existing widgets
            - 81-100: Perfect setup with GTM and existing chat patterns
            """
            
            result = await self._call_openai_structured(prompt, ChatReadinessAnalysis)
            
            score.chat_ready_score = min(100, max(0, result.score))
            score.signals_data['chat_readiness'] = result.model_dump()
            
            logger.info(f"Chat readiness score: {score.chat_ready_score}/100")
            
        except Exception as e:
            logger.error(f"Error analyzing chat readiness: {e}")
            score.chat_ready_score = 0

    async def _call_openai_structured(self, prompt: str, response_model: Type[BaseModel]) -> BaseModel:
        """Make OpenAI API call with structured outputs"""
        try:
            # Build API call parameters based on model support
            api_params = {
                "model": self.openai_model,
                "messages": [
                    {"role": "system", "content": "You are an expert at analyzing companies for AI chatbot sales opportunities."},
                    {"role": "user", "content": prompt}
                ],
                "response_format": response_model
            }
            
            # Add model-specific parameters based on OpenAI documentation
            # GPT-4o, GPT-4, and GPT-3.5 models support max_tokens and temperature
            if self.openai_model.startswith(("gpt-4o", "gpt-4", "gpt-3.5")):
                max_tokens = int(os.getenv("LEAD_SCORING_MAX_TOKENS", "1500"))
                temperature = float(os.getenv("LEAD_SCORING_TEMPERATURE", "0.3"))
                api_params["max_tokens"] = max_tokens
                api_params["temperature"] = temperature
                logger.info(f"Using model {self.openai_model} with max_tokens={max_tokens}, temperature={temperature}")
            else:
                logger.info(f"Using model {self.openai_model} with OpenAI defaults (no custom max_tokens/temperature)")
            
            response = self.enricher.client.beta.chat.completions.parse(**api_params)
            
            parsed = response.choices[0].message.parsed
            if parsed:
                return parsed
            # Fallback if parsed not available
            logger.warning("Structured parse returned no parsed payload; using default response")
            return self._build_default_response(response_model)
            
        except Exception as e:
            logger.error(f"OpenAI structured API error: {e}")
            # Return default low-score response with required fields populated
            return self._build_default_response(response_model)

    def _build_default_response(self, model_cls: Type[BaseModel]) -> BaseModel:
        """Build a safe default instance for any response model with required fields."""
        defaults: Dict[str, object] = {}
        for field_name, field in model_cls.model_fields.items():
            # Prefer explicit defaults if provided
            if field.default is not None:
                defaults[field_name] = field.default
                continue
            # Common fields
            if field_name == 'score':
                defaults[field_name] = 0
                continue
            if field_name == 'reasoning':
                defaults[field_name] = "Analysis failed due to API error"
                continue
            # Type-based defaults
            annotation = field.annotation
            origin = get_origin(annotation)
            args = get_args(annotation)
            try:
                if annotation in (int,):
                    defaults[field_name] = 0
                elif annotation in (float,):
                    defaults[field_name] = 0.0
                elif annotation in (bool,):
                    defaults[field_name] = False
                elif annotation in (str,):
                    defaults[field_name] = ""
                elif origin in (list, List):
                    defaults[field_name] = []
                elif origin in (dict, Dict):
                    defaults[field_name] = {}
                else:
                    # Fallback
                    defaults[field_name] = None
            except Exception:
                defaults[field_name] = None
        return model_cls(**defaults)

# Convenience functions for easy usage

async def score_company_by_id(company_id: int, progress_callback: Optional[Callable[[str, int, int], Awaitable[None]]] = None) -> LeadScore:
    """Score a single company by ID"""
    engine = LeadScoringEngine()
    return await engine.score_company(company_id, progress_callback)

async def score_multiple_companies(company_ids: List[int]) -> List[LeadScore]:
    """Score multiple companies in batch"""
    engine = LeadScoringEngine()
    results = []
    
    for company_id in company_ids:
        try:
            score = await engine.score_company(company_id)
            results.append(score)
            # Rate limiting between companies
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Failed to score company {company_id}: {e}")
            continue
    
    return results

def save_lead_score_to_db(score: LeadScore):
    """Save lead score results to database"""
    db = next(get_db_session())
    try:
        company = db.query(Company).filter(Company.id == score.company_id).first()
        if company:
            # Update company with lead scoring results
            company.lead_score = score.overall_score
            company.support_intensity_score = score.support_intensity_total
            company.growth_signals_score = score.growth_signals_total
            company.implementation_feasibility_score = score.implementation_feasibility_total
            company.digital_presence_score = score.digital_presence_total
            company.lead_scoring_data = score.signals_data
            company.lead_scored_at = datetime.now()
            
            db.commit()
            logger.info(f"Saved lead score for {company.name}: {score.overall_score}/400")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving lead score to database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    # Example usage
    import asyncio
    
    async def main():
        # Show configuration
        engine = LeadScoringEngine()
        config = engine.get_configuration()
        print("Lead Scoring Configuration:")
        for key, value in config.items():
            print(f"  {key}: {value}")
        print()
        
        # Score a specific company
        score = await score_company_by_id(1)
        print(f"Company: {score.company_name}")
        print(f"Overall Score: {score.overall_score}/400")
        print(f"Support Intensity: {score.support_intensity_total}/500")
        print(f"Growth Signals: {score.growth_signals_total}/300") 
        print(f"Implementation Feasibility: {score.implementation_feasibility_total}/400")
        print(f"Digital Presence: {score.digital_presence_total}/400")
        
        # Save to database
        save_lead_score_to_db(score)
    
    asyncio.run(main())