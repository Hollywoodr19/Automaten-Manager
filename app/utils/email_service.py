# app/utils/email_service.py
"""
E-Mail Service für Automaten Manager
Sendet Benachrichtigungen, Reports und Warnungen
"""

from flask import render_template_string, current_app
from flask_mail import Mail, Message
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
import os
from app import db
from app.models import User, Device, Product, MaintenanceRecord, Entry, Expense
from sqlalchemy import func

mail = Mail()

class EmailService:
    """E-Mail Service für verschiedene Benachrichtigungen"""
    
    @staticmethod
    def init_app(app):
        """Mail-Extension initialisieren"""
        mail.init_app(app)
    
    @staticmethod
    def send_email(to: str, subject: str, template: str, **kwargs):
        """Generische E-Mail senden"""
        try:
            msg = Message(
                subject=subject,
                recipients=[to],
                sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@automaten-manager.de')
            )
            
            # HTML-Template rendern
            msg.html = render_template_string(template, **kwargs)
            
            # Text-Version (vereinfacht)
            msg.body = msg.html.replace('<br>', '\n').replace('</p>', '\n')
            
            mail.send(msg)
            return True
        except Exception as e:
            current_app.logger.error(f"E-Mail senden fehlgeschlagen: {str(e)}")
            return False
    
    @classmethod
    def send_maintenance_reminder(cls, device: Device, user: User):
        """Wartungserinnerung senden"""
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; }
                .warning { background: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; margin: 10px 0; }
                .button { display: inline-block; padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; }
                .footer { background: #f4f4f4; padding: 10px; text-align: center; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>⚠️ Wartungserinnerung</h1>
            </div>
            <div class="content">
                <p>Hallo {{ user.username }},</p>
                
                <div class="warning">
                    <strong>Das Gerät "{{ device.name }}" benötigt eine Wartung!</strong>
                </div>
                
                <p><strong>Geräte-Details:</strong></p>
                <ul>
                    <li>Gerät: {{ device.name }}</li>
                    <li>Standort: {{ device.location or 'Nicht angegeben' }}</li>
                    <li>Seriennummer: {{ device.serial_number }}</li>
                    <li>Letzte Wartung: {{ last_maintenance }}</li>
                    <li>Tage überfällig: {{ days_overdue }}</li>
                </ul>
                
                <p>Bitte planen Sie baldmöglichst eine Wartung ein, um Ausfälle zu vermeiden.</p>
                
                <p style="text-align: center;">
                    <a href="{{ url }}" class="button">Zur Wartungsplanung</a>
                </p>
                
                <p>Mit freundlichen Grüßen,<br>
                Ihr Automaten-Manager</p>
            </div>
            <div class="footer">
                Diese E-Mail wurde automatisch generiert. Bitte antworten Sie nicht auf diese E-Mail.
            </div>
        </body>
        </html>
        """
        
        # Letzte Wartung ermitteln
        last_maintenance = MaintenanceRecord.query.filter_by(
            device_id=device.id
        ).order_by(MaintenanceRecord.date.desc()).first()
        
        last_maintenance_date = last_maintenance.date if last_maintenance else "Noch nie"
        days_overdue = (date.today() - last_maintenance.date).days if last_maintenance else 999
        
        return cls.send_email(
            to=user.email,
            subject=f"Wartung fällig: {device.name}",
            template=template,
            user=user,
            device=device,
            last_maintenance=last_maintenance_date,
            days_overdue=days_overdue,
            url=f"{current_app.config.get('APP_URL', 'http://localhost:5000')}/devices/maintenance"
        )
    
    @classmethod
    def send_low_stock_alert(cls, product: Product, user: User):
        """Niedrigbestand-Warnung senden"""
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; }
                .alert { background: #f8d7da; border-left: 4px solid #dc3545; padding: 10px; margin: 10px 0; }
                .button { display: inline-block; padding: 10px 20px; background: #28a745; color: white; text-decoration: none; border-radius: 5px; }
                .stock-table { width: 100%; border-collapse: collapse; margin: 20px 0; }
                .stock-table th, .stock-table td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
                .stock-table th { background: #f4f4f4; }
                .footer { background: #f4f4f4; padding: 10px; text-align: center; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📦 Niedrigbestand-Warnung</h1>
            </div>
            <div class="content">
                <p>Hallo {{ user.username }},</p>
                
                <div class="alert">
                    <strong>Achtung: Niedriger Lagerbestand!</strong>
                </div>
                
                <table class="stock-table">
                    <tr>
                        <th>Produkt</th>
                        <th>Aktueller Bestand</th>
                        <th>Mindestbestand</th>
                        <th>Status</th>
                    </tr>
                    <tr>
                        <td><strong>{{ product.name }}</strong></td>
                        <td>{{ current_stock }} {{ product.unit.value }}</td>
                        <td>{{ product.reorder_point }} {{ product.unit.value }}</td>
                        <td style="color: red;">⚠️ Nachbestellen</td>
                    </tr>
                </table>
                
                <p>Bitte bestellen Sie rechtzeitig nach, um Engpässe zu vermeiden.</p>
                
                <p style="text-align: center;">
                    <a href="{{ url }}" class="button">Jetzt nachbestellen</a>
                </p>
                
                <p>Mit freundlichen Grüßen,<br>
                Ihr Automaten-Manager</p>
            </div>
            <div class="footer">
                Diese E-Mail wurde automatisch generiert. Sie können die Benachrichtigungseinstellungen in Ihrem Profil anpassen.
            </div>
        </body>
        </html>
        """
        
        current_stock = product.get_current_stock()
        
        return cls.send_email(
            to=user.email,
            subject=f"Niedrigbestand: {product.name}",
            template=template,
            user=user,
            product=product,
            current_stock=current_stock,
            url=f"{current_app.config.get('APP_URL', 'http://localhost:5000')}/products"
        )
    
    @classmethod
    def send_daily_summary(cls, user: User):
        """Tägliche Zusammenfassung senden"""
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        # Statistiken sammeln
        daily_revenue = db.session.query(func.sum(Entry.amount)).filter(
            Entry.date == yesterday
        ).scalar() or 0
        
        daily_expenses = db.session.query(func.sum(Expense.amount)).filter(
            Expense.date == yesterday
        ).scalar() or 0
        
        daily_profit = daily_revenue - daily_expenses
        
        # Aktive Geräte
        active_devices = Device.query.filter_by(
            owner_id=user.id,
            status='active'
        ).count()
        
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; }
                .stats { display: flex; justify-content: space-around; margin: 20px 0; }
                .stat-box { text-align: center; padding: 15px; background: #f8f9fa; border-radius: 8px; }
                .stat-value { font-size: 24px; font-weight: bold; margin: 5px 0; }
                .stat-label { color: #666; font-size: 14px; }
                .positive { color: #28a745; }
                .negative { color: #dc3545; }
                .button { display: inline-block; padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; }
                .footer { background: #f4f4f4; padding: 10px; text-align: center; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 Tägliche Zusammenfassung</h1>
                <p>{{ yesterday.strftime('%d.%m.%Y') }}</p>
            </div>
            <div class="content">
                <p>Hallo {{ user.username }},</p>
                
                <p>hier ist Ihre tägliche Zusammenfassung:</p>
                
                <div class="stats">
                    <div class="stat-box">
                        <div class="stat-label">Einnahmen</div>
                        <div class="stat-value positive">+{{ "%.2f"|format(daily_revenue) }} €</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-label">Ausgaben</div>
                        <div class="stat-value negative">-{{ "%.2f"|format(daily_expenses) }} €</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-label">Gewinn</div>
                        <div class="stat-value {% if daily_profit >= 0 %}positive{% else %}negative{% endif %}">
                            {{ "%.2f"|format(daily_profit) }} €
                        </div>
                    </div>
                </div>
                
                <p><strong>Status:</strong></p>
                <ul>
                    <li>Aktive Geräte: {{ active_devices }}</li>
                    <li>Anstehende Wartungen: {{ pending_maintenance }}</li>
                    <li>Niedrige Bestände: {{ low_stock_count }}</li>
                </ul>
                
                <p style="text-align: center;">
                    <a href="{{ url }}" class="button">Zum Dashboard</a>
                </p>
                
                <p>Mit freundlichen Grüßen,<br>
                Ihr Automaten-Manager</p>
            </div>
            <div class="footer">
                Sie erhalten diese E-Mail, weil Sie tägliche Zusammenfassungen aktiviert haben.<br>
                <a href="{{ unsubscribe_url }}">Abmelden</a>
            </div>
        </body>
        </html>
        """
        
        # Weitere Statistiken
        pending_maintenance = 0  # TODO: Implementieren
        low_stock_count = Product.query.filter(
            Product.user_id == user.id,
            Product.current_stock <= Product.reorder_point
        ).count() if hasattr(Product, 'current_stock') else 0
        
        return cls.send_email(
            to=user.email,
            subject=f"Tägliche Zusammenfassung - {yesterday.strftime('%d.%m.%Y')}",
            template=template,
            user=user,
            yesterday=yesterday,
            daily_revenue=daily_revenue,
            daily_expenses=daily_expenses,
            daily_profit=daily_profit,
            active_devices=active_devices,
            pending_maintenance=pending_maintenance,
            low_stock_count=low_stock_count,
            url=f"{current_app.config.get('APP_URL', 'http://localhost:5000')}/dashboard",
            unsubscribe_url=f"{current_app.config.get('APP_URL', 'http://localhost:5000')}/settings/notifications"
        )
    
    @classmethod
    def send_test_email(cls, user: User):
        """Test-E-Mail senden"""
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; }
                .success { background: #d4edda; border-left: 4px solid #28a745; padding: 10px; margin: 10px 0; }
                .footer { background: #f4f4f4; padding: 10px; text-align: center; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>✉️ Test-E-Mail</h1>
            </div>
            <div class="content">
                <p>Hallo {{ user.username }},</p>
                
                <div class="success">
                    <strong>✅ E-Mail-Versand funktioniert!</strong>
                </div>
                
                <p>Diese Test-E-Mail bestätigt, dass Ihre E-Mail-Benachrichtigungen korrekt konfiguriert sind.</p>
                
                <p><strong>Ihre E-Mail-Einstellungen:</strong></p>
                <ul>
                    <li>E-Mail-Adresse: {{ user.email }}</li>
                    <li>Zeitstempel: {{ timestamp }}</li>
                    <li>Server: {{ server_info }}</li>
                </ul>
                
                <p>Mit freundlichen Grüßen,<br>
                Ihr Automaten-Manager</p>
            </div>
            <div class="footer">
                Dies ist eine Test-E-Mail zur Überprüfung der E-Mail-Konfiguration.
            </div>
        </body>
        </html>
        """
        
        return cls.send_email(
            to=user.email,
            subject="Test-E-Mail von Automaten-Manager",
            template=template,
            user=user,
            timestamp=datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
            server_info=current_app.config.get('MAIL_SERVER', 'Nicht konfiguriert')
        )


# Scheduled Tasks (mit Flask-APScheduler oder Celery)
class EmailScheduler:
    """Geplante E-Mail-Tasks"""
    
    @staticmethod
    def check_maintenance_due():
        """Prüft täglich auf fällige Wartungen"""
        devices = Device.query.all()
        
        for device in devices:
            # Letzte Wartung prüfen
            last_maintenance = MaintenanceRecord.query.filter_by(
                device_id=device.id
            ).order_by(MaintenanceRecord.date.desc()).first()
            
            if last_maintenance:
                days_since = (date.today() - last_maintenance.date).days
                
                # Warnung bei 85 Tagen (5 Tage vor fällig)
                if days_since == 85:
                    EmailService.send_maintenance_reminder(device, device.owner)
                # Erinnerung bei 90 Tagen
                elif days_since >= 90:
                    EmailService.send_maintenance_reminder(device, device.owner)
    
    @staticmethod
    def check_low_stock():
        """Prüft täglich auf niedrige Bestände"""
        products = Product.query.all()
        
        for product in products:
            if hasattr(product, 'get_current_stock'):
                current_stock = product.get_current_stock()
                if product.reorder_point and current_stock <= product.reorder_point:
                    EmailService.send_low_stock_alert(product, product.user)
    
    @staticmethod
    def send_daily_summaries():
        """Sendet tägliche Zusammenfassungen an alle User mit aktivierter Option"""
        users = User.query.filter_by(
            daily_summary_enabled=True  # Neues Feld in User-Model
        ).all()
        
        for user in users:
            EmailService.send_daily_summary(user)
