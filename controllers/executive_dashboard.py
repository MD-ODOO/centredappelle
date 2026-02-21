from odoo import http, fields
from odoo.http import request
from datetime import datetime
from dateutil.relativedelta import relativedelta


class ExecutiveDashboard(http.Controller):

    @http.route('/executive/dashboard/data', type='json', auth='user')
    def get_dashboard_data(self, period='month'):

        today = fields.Date.today()

        if period == 'week':
            date_start = today - relativedelta(days=7)
        elif period == 'quarter':
            date_start = today - relativedelta(months=3)
        elif period == 'year':
            date_start = today - relativedelta(years=1)
        else:
            date_start = today - relativedelta(months=1)

        domain = [
            ('start', '>=', date_start),
            ('start', '<=', today)
        ]

        events = request.env['calendar.event'].sudo().search(domain)

        return {
            'global': self._get_global_kpi(events),
            'conseillers': self._get_conseiller_kpi(events, date_start, today),
            'campagnes': self._get_campaign_kpi(events),
            'period': period,
        }

    # ---------------- GLOBAL KPI ----------------

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

    # ---------------- KPI CONSEILLERS ----------------

    def _get_conseiller_kpi(self, events, date_start, date_end):

        data = {}
        days = (date_end - date_start).days + 1
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

    # ---------------- KPI CAMPAGNES ----------------

    def _get_campaign_kpi(self, events):

        campaigns = request.env['oui.campaign'].sudo().search([])

        result = []

        for campaign in campaigns:

            ev = events.filtered(lambda e: e.campaign_id.id == campaign.id)

            pris = len(ev)
            exploite = len(ev.filtered(lambda e: e.stage_id.is_done))
            absent = len(ev.filtered(lambda e: e.stage_id.name == "Absent"))

            result.append({
                'id': campaign.id,
                'name': campaign.name,
                'commandes': campaign.monthly_rdv_volume,
                'pris': pris,
                'exploite': exploite,
                'absent': absent,
                'restant': campaign.total_volume - campaign.rdv_realised,
                'performance': (exploite / pris * 100) if pris else 0,
                'price': campaign.price,
            })

        return result