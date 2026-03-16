from odoo import http, fields
from odoo.http import request
from datetime import datetime
from dateutil.relativedelta import relativedelta


class ExecutiveDashboardController(http.Controller):

    # ----------------------------------------------------
    # KPI CAMPAGNE PAR JOUR
    # ----------------------------------------------------

    @http.route('/campaign/<int:campaign_id>/kpi', type='json', auth='user')
    def campaign_kpi(self, campaign_id):

        campaign = request.env['oui.campaign'].sudo().browse(campaign_id)

        if not campaign.exists():
            return []

        return campaign.get_campaign_daily_kpi()

    # ----------------------------------------------------
    # DASHBOARD DATA
    # ----------------------------------------------------

    @http.route('/executive/dashboard/data', type='json', auth='user')
    def get_dashboard_data(self, period='month'):

        today = fields.Date.today()

        start_date, end_date = self._compute_period(period, today)

        Event = request.env['calendar.event'].sudo()

        events = Event.search([
            ('start', '>=', start_date),
            ('start', '<=', end_date)
        ])

        Stage = request.env['rdv.stage'].sudo()

        absent_stage = Stage.search([('name', '=', 'Absent')], limit=1)
        report_stage = Stage.search([('name', '=', 'Reporté')], limit=1)

        global_kpi = self._get_global_kpi(events, absent_stage)

        conseillers_kpi = self._get_conseiller_kpi(
            events,
            start_date,
            end_date,
            absent_stage
        )

        campagnes_kpi = self._get_campaign_kpi(
            events,
            absent_stage,
            report_stage
        )

        return {
            'period': period,
            'is_admin': request.env.user.has_group(
                'oui_allo_rdv_pro.group_call_admin'
            ),
            'global': global_kpi,
            'conseillers': conseillers_kpi,
            'campagnes': campagnes_kpi,
        }

    # ----------------------------------------------------
    # COMPUTE PERIOD
    # ----------------------------------------------------

    def _compute_period(self, period, today):

        if period == 'week':

            start = today - relativedelta(days=today.weekday())
            end = start + relativedelta(days=6)

        elif period == 'previous_week':

            start = today - relativedelta(days=today.weekday() + 7)
            end = start + relativedelta(days=6)

        elif period == 'month':

            start = today.replace(day=1)
            end = today

        elif period == 'previous_month':

            first_day = today.replace(day=1)
            end = first_day - relativedelta(days=1)
            start = end.replace(day=1)

        elif period == 'quarter':

            quarter = (today.month - 1) // 3 + 1
            start = datetime(today.year, 3 * quarter - 2, 1).date()
            end = start + relativedelta(months=3, days=-1)

        elif period == 'previous_quarter':

            quarter = (today.month - 1) // 3 + 1
            prev_quarter = quarter - 1 or 4

            year = today.year if quarter > 1 else today.year - 1

            start = datetime(year, 3 * prev_quarter - 2, 1).date()
            end = start + relativedelta(months=3, days=-1)

        elif period == 'year':

            start = datetime(today.year, 1, 1).date()
            end = datetime(today.year, 12, 31).date()

        else:

            start = datetime(today.year - 1, 1, 1).date()
            end = datetime(today.year - 1, 12, 31).date()

        return start, end

    # ----------------------------------------------------
    # GLOBAL KPI
    # ----------------------------------------------------

    def _get_global_kpi(self, events, absent_stage):

        total = len(events)

        exploite = len(events.filtered(lambda e: e.stage_id.is_done))

        absent = len(events.filtered(
            lambda e: absent_stage and e.stage_id.id == absent_stage.id
        ))

        return {
            'total': total,
            'exploite': exploite,
            'absent': absent,
            'taux_exploitation': round(exploite / total * 100, 2) if total else 0,
            'taux_no_show': round(absent / total * 100, 2) if total else 0,
        }

    # ----------------------------------------------------
    # CONSEILLER KPI
    # ----------------------------------------------------

    def _get_conseiller_kpi(self, events, start_date, end_date, absent_stage):

        env = request.env

        Event = env['calendar.event'].sudo()

        days = (end_date - start_date).days + 1

        objectif = round((days / 3) * 2)

        grouped = Event.read_group(
            [
                ('start', '>=', start_date),
                ('start', '<=', end_date),
                ('conseiller_id', '!=', False)
            ],
            ['conseiller_id', 'stage_id'],
            ['conseiller_id', 'stage_id'],
            lazy=False
        )

        data = {}

        for group in grouped:

            conseiller_id = group['conseiller_id'][0]
            conseiller_name = group['conseiller_id'][1]
            stage = group.get('stage_id')
            count = group.get('__count', 0)

            if conseiller_id not in data:

                data[conseiller_id] = {
                    'id': conseiller_id,
                    'name': conseiller_name,
                    'pris': 0,
                    'exploite': 0,
                    'absent': 0,
                    'objectif': objectif
                }

            data[conseiller_id]['pris'] += count

            if stage:

                stage_record = env['rdv.stage'].browse(stage[0])

                if stage_record.is_done:
                    data[conseiller_id]['exploite'] += count

                if absent_stage and stage[0] == absent_stage.id:
                    data[conseiller_id]['absent'] += count

        for c in data.values():

            pris = c['pris']
            exploite = c['exploite']
            absent = c['absent']

            c['taux_exploitation'] = round(
                exploite / pris * 100, 2
            ) if pris else 0

            c['taux_no_show'] = round(
                absent / pris * 100, 2
            ) if pris else 0

            c['objectif_atteint'] = exploite >= objectif

        return list(data.values())

    # ----------------------------------------------------
    # CAMPAIGN KPI
    # ----------------------------------------------------

    def _get_campaign_kpi(self, events, absent_stage, report_stage):

        campaigns = request.env['oui.campaign'].sudo().search([])

        result = []

        for campaign in campaigns:

            ev = events.filtered(
                lambda e: e.campaign_id.id == campaign.id
            )

            pris = len(ev)

            exploite = len(ev.filtered(lambda e: e.stage_id.is_done))

            absent = len(ev.filtered(
                lambda e: absent_stage and e.stage_id.id == absent_stage.id
            ))

            reportes = len(ev.filtered(
                lambda e: report_stage and e.stage_id.id == report_stage.id
            ))

            result.append({
                'id': campaign.id,
                'name': campaign.name,
                'commande': campaign.monthly_rdv_volume,
                'pris': pris,
                'exploite': exploite,
                'absent': absent,
                'reporte': reportes,
                'restant': campaign.total_volume - campaign.rdv_realised,
                'taux_exploitation': round(
                    exploite / pris * 100, 2
                ) if pris else 0,
                'price_paid': campaign.price,
                'conseillers': [],
            })

        return result