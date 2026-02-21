from odoo import http, fields
from odoo.http import request
from datetime import datetime
from dateutil.relativedelta import relativedelta

class ExecutiveDashboard(http.Controller):

    @http.route('/executive/dashboard/data', type='json', auth='user')
    def get_dashboard_data(self, period='month'):
        today = fields.Date.today()

        # Calcul période
        if period == 'week':
            start_date = today - relativedelta(days=today.weekday())
            end_date = start_date + relativedelta(days=6)
        elif period == 'month':
            start_date = today.replace(day=1)
            end_date = start_date + relativedelta(months=1, days=-1)
        elif period == 'quarter':
            quarter = (today.month - 1) // 3 + 1
            start_date = datetime(today.year, 3*quarter-2, 1).date()
            end_date = start_date + relativedelta(months=3, days=-1)
        elif period == 'year':
            start_date = datetime(today.year, 1, 1).date()
            end_date = datetime(today.year, 12, 31).date()
        else:
            start_date = today - relativedelta(months=1)
            end_date = today

        events = request.env['calendar.event'].sudo().search([
            ('start', '>=', start_date),
            ('start', '<=', end_date)
        ])

        return {
            'global': self._get_global_kpi(events),
            'conseillers': self._get_conseiller_kpi(events, start_date, end_date),
            'campagnes': self._get_campaign_kpi(events),
            'period': period,
            'is_admin': request.env.user.has_group('oui_allo_rdv_pro.group_call_admin')
        }

    # --- GLOBAL KPI ---
    def _get_global_kpi(self, events):
        total = len(events)
        exploite = len(events.filtered(lambda e: e.stage_id.is_done))
        absent = len(events.filtered(lambda e: e.stage_id.name == "Absent"))
        return {
            'total': total,
            'exploite': exploite,
            'absent': absent,
            'taux_exploitation': (exploite / total * 100) if total else 0,
            'taux_no_show': (absent / total * 100) if total else 0,
        }

    # --- CONSEILLERS KPI ---
    def _get_conseiller_kpi(self, events, start_date, end_date):
        data = {}
        days = (end_date - start_date).days + 1
        objectif = round((days / 3) * 2)

        for event in events:
            for conseiller in event.conseiller_id:
                if conseiller.id not in data:
                    data[conseiller.id] = {
                        'id': conseiller.id,
                        'name': conseiller.name,
                        'pris': 0,
                        'exploite': 0,
                        'absent': 0,
                        'objectif': objectif,
                    }
                data[conseiller.id]['pris'] += 1
                if event.stage_id.is_done:
                    data[conseiller.id]['exploite'] += 1
                if event.stage_id.name == "Absent":
                    data[conseiller.id]['absent'] += 1

        for c in data.values():
            pris = c['pris']
            exploite = c['exploite']
            absent = c['absent']
            c['taux_exploitation'] = (exploite / pris * 100) if pris else 0
            c['taux_no_show'] = (absent / pris * 100) if pris else 0
            c['objectif_atteint'] = exploite >= objectif

        return list(data.values())

    # --- CAMPAGNES KPI ---
    def _get_campaign_kpi(self, events):
        campaigns = request.env['oui.campaign'].sudo().search([])
        result = []
        for campaign in campaigns:
            ev = events.filtered(lambda e: e.campaign_id.id == campaign.id)
            pris = len(ev)
            exploite = len(ev.filtered(lambda e: e.stage_id.is_done))
            absent = len(ev.filtered(lambda e: e.stage_id.name == "Absent"))
            reportes = len(ev.filtered(lambda e: e.stage_id.name == "Reporté"))
            result.append({
                'id': campaign.id,
                'name': campaign.name,
                'commande': campaign.monthly_rdv_volume,
                'pris': pris,
                'exploite': exploite,
                'absent': absent,
                'reporte': reportes,
                'restant': campaign.total_volume - campaign.rdv_realised,
                'taux_exploitation': (exploite / pris * 100) if pris else 0,
                'price_paid': campaign.price,
                'conseillers': [],  # éventuellement remplir par campagne
            })
        return result