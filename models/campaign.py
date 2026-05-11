from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime,timedelta
from dateutil.relativedelta import relativedelta




class Campaign(models.Model):
    _name = 'oui.campaign'
    _description = 'Campagne'
    _order = 'id desc'
    _inherit = ['mail.thread']  # pour tracking state

    @api.model
    def _default_user_id(self):
        return self.env.user

    def _user_domain(self):
        
        return [('id', '=', self.env.user.id)]

    name = fields.Char(string="Référence", readonly=True, copy=False)
    client_id = fields.Many2one(
        'res.partner',
        string="Client",
        required=True,
        domain="[('is_company','=',True)]"
    )
    conseiller_ids = fields.Many2many('res.users', string="Conseillers")

    attendee_ids = fields.One2many(
        'calendar.event',
        'campaign_id',
        string="Rendez-vous"
    )
    campaign_manager_id = fields.Many2one(
    'res.users',
    string="Responsable de campagne"
    )

    event_count = fields.Integer(
        string="Rendez-Vous",
        store=True,
        compute="_compute_counts"
    )

    attendee_count = fields.Integer(
        string="Nombre de RDV",
        compute="_compute_counts"
    )

    state = fields.Selection([
    ('draft', 'Brouillon'),
    ('open', 'Active'),
    ('expiring', 'À expirer bientôt'),
    ('closed', 'Fermée'),
       ], tracking=True, compute="_compute_state", store=True)
    

    monthly_rdv_volume = fields.Integer(
        string="Volume de RDV commandé / mois",store=True
    )

    rdv_carry_over = fields.Boolean(
        string="RDV reportables si non consommés"
    )

    price = fields.Monetary(
    string="Prix",
    currency_field='currency_id',
    groups="oui_allo_rdv_pro.group_call_admin"
)

    contract_attachment_ids = fields.Many2many(
    'ir.attachment',
    'campaign_attachment_rel',
    'campaign_id',
    'attachment_id',
    string="Contrats"
)


    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )

    agenda_id = fields.Many2one(
        'resource.resource',
        string="Agenda affilié unique"
    )
    
    total_volume = fields.Integer(
    string="Volume total contractuel",
    compute="_compute_total_volume",
    store=True
    )
    rdv_realised = fields.Integer(
    string="RDV réalisés",
    compute="_compute_rdv_stats",
    store=True
    )

    rdv_remaining = fields.Integer(
        string="RDV restants",
        compute="_compute_rdv_stats",
        store=True
    )

    completion_rate = fields.Float(
    string="Taux de réalisation (%)",
    compute="_compute_completion_rate",
    store=True
    )

    invoice_id = fields.Many2one(
    'account.move',
    string="Facture",
    readonly=True,
    copy=False
    )
    rdv_month_count = fields.Integer('Rendez-Vous Mensuel', compute="_compute_rdv_month_count",store=True )

    invoice_count = fields.Integer( string='Factures',
        compute="_compute_invoice_count"
    )

    activity_id=fields.Many2one('activity.agence', 'Activité')

    date_start = fields.Date(string="Date de début", required=True)
    date_end = fields.Date(string="Date de fin", required=True)

    duration_months = fields.Integer(
    string="Durée calculée (mois)",
    compute="_compute_duration",
    store=True
)
    

    @api.depends('date_start', 'date_end')
    def _compute_duration(self):
        for rec in self:
            if rec.date_start and rec.date_end:
                delta = relativedelta(rec.date_end, rec.date_start)
                rec.duration_months = delta.years * 12 + delta.months + 1
            else:
                rec.duration_months = 0


    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for rec in self:
            if rec.date_start and rec.date_end:
                if rec.date_end < rec.date_start:
                    raise ValidationError("La date de fin doit être postérieure à la date de début.")


    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = 1 if rec.invoice_id else 0
    

    def action_view_invoice(self):
        self.ensure_one()

        # 1️⃣ Si facture existe déjà → ouvrir
        if self.invoice_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': self.invoice_id.id,
            }

        # 2️⃣ Sinon → validations
        if not self.price:
            raise ValidationError("Le prix de la campagne est obligatoire.")

        if not self.client_id:
            raise ValidationError("Client obligatoire.")

        # 3️⃣ Création facture
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.client_id.id,
            'invoice_origin': self.name,
            'campaign_id': self.id,  # si champ ajouté dans account.move
            'invoice_line_ids': [(0, 0, {
                'name': f"Campagne {self.name}",
                'quantity': 1,
                'price_unit': self.price,
            })]
        })

        # 4️⃣ Lier à la campagne
        self.invoice_id = invoice.id

        # 5️⃣ Ouvrir facture créée
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': invoice.id,
        }


    @api.depends('rdv_realised', 'total_volume')
    def _compute_completion_rate(self):
        for rec in self:
            if rec.total_volume:
                rec.completion_rate = (rec.rdv_realised / rec.total_volume) * 100
            else:
                rec.completion_rate = 0

    @api.depends('date_start', 'date_end', 'monthly_rdv_volume')
    def _compute_total_volume(self):
        for rec in self:
            if rec.date_start and rec.date_end:
                delta = relativedelta(rec.date_end, rec.date_start)
                months = delta.years * 12 + delta.months + 1
            else:
                months = 0

            rec.total_volume = months * (rec.monthly_rdv_volume or 0)


    # ------------------------
    # BOUTONS
    # ------------------------

    @api.constrains('duration_months', 'monthly_rdv_volume')
    def _check_positive_values(self):
        for rec in self:
            if rec.duration_months and rec.duration_months < 0:
                raise ValidationError("La durée ne peut pas être négative.")
            if rec.monthly_rdv_volume and rec.monthly_rdv_volume < 0:
                raise ValidationError("Le volume mensuel ne peut pas être négatif.")

    def action_close(self):
        self.write({'state': 'closed'})

    def action_reopen(self):
        self.write({'state': 'open'})

    # ------------------------
    # VALIDATION CLIENT
    # ------------------------

    @api.constrains('client_id')
    def _check_client_company(self):
        for rec in self:
            if rec.client_id and not rec.client_id.is_company:
                raise ValidationError("Le client doit être une société.")

    # ------------------------
    # SEQUENCE AUTOMATIQUE
    # ------------------------

    @api.model_create_multi
    def create(self, vals_list):

        for vals in vals_list:

            # Validation client obligatoire
            if not vals.get('client_id'):
                raise ValidationError(_("Le client est obligatoire."))

            if not vals.get('name') or vals.get('name') == '/':

                seq = self.env['ir.sequence'].next_by_code(
                    'oui.campaign'
                ) or '000'

                # 🔹 Client
                client_name = ""
                if vals.get('client_id'):
                    client = self.env['res.partner'].browse(
                        vals['client_id']
                    )
                    client_name = client.name or ""

                # 🔹 Activité
                activity_name = ""
                if vals.get('activity_id'):
                    activity = self.env['activity.agence'].browse(
                        vals['activity_id']
                    )
                    activity_name = activity.name or ""

                # 🔹 Date référence
                date_ref = vals.get('date_start') or fields.Date.today()
                date_obj = fields.Date.to_date(date_ref)

                month = date_obj.strftime("%B").capitalize()
                year = date_obj.strftime("%Y")
                day = date_obj.strftime("%d")

                # 🔹 Construction propre sans espaces inutiles
                parts = [
                    client_name,
                    activity_name,
                    f"{day} {month} {year}",
                    # seq
                ]

                vals['name'] = " - ".join([p for p in parts if p])

        return super().create(vals_list)



    # ------------------------
    # CREATION EVENEMENT
    # ------------------------

    


    # ------------------------
    # COMPTEURS OPTIMISÉS
    # ------------------------
    @api.depends('attendee_ids.campaign_id')
    def _compute_counts(self):

        # Initialiser à 0 pour TOUS les records
        for rec in self:
            rec.event_count = 0

        # Filtrer seulement les records déjà sauvegardés
        saved_records = self.filtered(lambda r: r.id)

        if not saved_records:
            return

        event_data = self.env['calendar.event'].read_group(
            [('campaign_id', 'in', saved_records.ids)],
            ['campaign_id'],
            ['campaign_id']
        )

        mapped_events = {
            data['campaign_id'][0]: data['campaign_id_count']
            for data in event_data
        }

        for rec in saved_records:
            rec.event_count = mapped_events.get(rec.id, 0)




    # ------------------------
    # PROTECTION SI FERMÉE
    # ------------------------

    @api.depends('total_volume','attendee_ids.stage_id')
    def _compute_rdv_stats(self):

        if not self.ids:
            return

        # RDV réalisés (étape finale)
        realised_data = self.env['calendar.event'].read_group(
            [
                ('campaign_id', 'in', self.ids),
                ('stage_id.is_done', '=', True)
            ],
            ['campaign_id'],
            ['campaign_id']
        )

        realised_map = {
            data['campaign_id'][0]: data['campaign_id_count']
            for data in realised_data
        }

        for rec in self:
            realised = realised_map.get(rec.id, 0)
            rec.rdv_realised = realised
            rec.rdv_remaining = max(rec.total_volume - realised, 0)

    @api.depends('attendee_ids.start')
    def _compute_rdv_month_count(self):

        today = fields.Date.today()
        month_start = today.replace(day=1)
        month_end = month_start + relativedelta(months=1)

        data = self.env['calendar.event'].read_group(
            [
                ('campaign_id', 'in', self.ids),
                ('start', '>=', month_start),
                ('start', '<', month_end),
            ],
            ['campaign_id'],
            ['campaign_id']
        )

        month_map = {
            d['campaign_id'][0]: d['campaign_id_count']
            for d in data
        }

        for rec in self:
            rec.rdv_month_count = month_map.get(rec.id, 0)



    def write(self, vals):
        if not self.env.context.get('bypass_state_lock'):
            for rec in self:
                if rec.state == 'closed' and any(
                    key not in ['state', 'message_follower_ids']
                    for key in vals.keys()
                ):
                    raise ValidationError("Impossible de modifier une campagne fermée.")

        return super().write(vals)

    
    @api.depends('date_start', 'date_end')
    def _compute_state(self):
        today = fields.Date.today()

        for rec in self:
            if not rec.date_start or not rec.date_end:
                rec.state = 'draft'
                continue

            if today < rec.date_start:
                rec.state = 'draft'
            elif rec.date_start <= today <= rec.date_end:
                # campagne active
                days_left = (rec.date_end - today).days
                if days_left <= 7:
                    rec.state = 'expiring'
                else:
                    rec.state = 'open'
            else:
                rec.state = 'closed'
    
    def action_open_generate_rdv_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Générer RDV',
            'res_model': 'campaign.generate.rdv.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_campaign_id': self.id,
                'default_partner_id': self.client_id.id,
                'default_responsable_id': self.campaign_manager_id.id,
                'default_conseiller_ids': [(6, 0, self.conseiller_ids.ids)]

            }
        }
    
    def action_view_realised(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'RDV Réalisés',
            'res_model': 'calendar.event',
            'view_mode': 'list,kanban,form,calendar',
            'domain': [
                ('campaign_id', '=', self.id),
                ('stage_id.is_done', '=', True)
            ],
        }
    
    def action_view_agenda(self):
        self.ensure_one()

        user = self.env.user

        if user.has_group('oui_allo_rdv_pro.group_call_admin'):
            domain = [('campaign_id', '=', self.id)]

        elif user.has_group('oui_allo_rdv_pro.group_call_manager'):
            domain = [
                ('campaign_id', '=', self.id),
                ('campaign_id.campaign_manager_id', '=', user.id)
            ]

        else:
            domain = [
                ('campaign_id', '=', self.id),
                ('conseiller_id', '=', user.id)
            ]

        return {
            'type': 'ir.actions.act_window',
            'name': 'Agenda',
            'res_model': 'calendar.event',
            'view_mode': 'calendar,tree,form,kanban',
            'domain': domain,
            'context': {
                'default_campaign_id': self.id,
                'search_default_today': 1,
            }
        }
    def action_view_campagne_evens(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Campagne RDV',
            'res_model': 'calendar.event',
            'view_mode': 'kanban,list,form,calendar',
            'domain': [
                ('campaign_id', '=', self.id) ],
        }
    


    @api.model
    def get_executive_dashboard_data(self, period="month"):

        today = fields.Date.today()

        start_date = today
        end_date = today

        # ========================
        # Détermination période
        # ========================

        if period == "week":

            start_date = today - timedelta(days=today.weekday())
            end_date = start_date + timedelta(days=6)

        elif period == "month":

            start_date = today.replace(day=1)
            end_date = start_date + relativedelta(months=1, days=-1)

        elif period == "quarter":

            quarter = (today.month - 1) // 3 + 1
            start_date = datetime(today.year, 3 * quarter - 2, 1).date()
            end_date = start_date + relativedelta(months=3, days=-1)

        elif period == "year":

            start_date = datetime(today.year, 1, 1).date()
            end_date = datetime(today.year, 12, 31).date()

        Event = self.env["calendar.event"].sudo()

        events = Event.search([
            ("start", ">=", start_date),
            ("start", "<=", end_date)
        ])

        # ========================
        # KPI GLOBAL
        # ========================

        total_rdv = len(events)

        exploite_rdv = len(
            events.filtered(lambda e: e.stage_id and e.stage_id.is_done)
        )

        absent_rdv = len(
            events.filtered(lambda e: e.stage_id and e.stage_id.name == "Absent")
        )

        global_data = {
            "total": total_rdv,
            "exploite": exploite_rdv,
            "absent": absent_rdv,
            "taux_exploitation": round((exploite_rdv / total_rdv * 100), 2) if total_rdv else 0,
            "taux_no_show": round((absent_rdv / total_rdv * 100), 2) if total_rdv else 0,
        }

        # ========================
        # KPI AUJOURD'HUI
        # ========================

        today_events = events.filtered(
            lambda e: e.start and e.start.date() == today
        )

        today_data = {
            "total": len(today_events),
            "exploite": len(today_events.filtered(lambda e: e.stage_id and e.stage_id.is_done)),
            "absent": len(today_events.filtered(lambda e: e.stage_id and e.stage_id.name == "Absent")),
            "conseillers": len(set(today_events.mapped("conseiller_id.id")))
        }

        # ========================
        # CONSEILLERS
        # ========================

        conseillers = self.env["res.users"].sudo().search([
            ("share", "=", False),
            ("active", "=", True)
        ])

        days = (end_date - start_date).days + 1
        objectif = round((days / 3) * 2)

        conseillers_data = []

        for c in conseillers:

            c_events = events.filtered(lambda e: e.conseiller_id and e.conseiller_id.id == c.id)

            pris = len(c_events)

            exploite = len(c_events.filtered(lambda e: e.stage_id and e.stage_id.is_done))

            absent = len(c_events.filtered(lambda e: e.stage_id and e.stage_id.name == "Absent"))

            taux = round((exploite / pris * 100), 2) if pris else 0

            conseillers_data.append({
                "id": c.id,
                "name": c.name,
                "pris": pris,
                "exploite": exploite,
                "absent": absent,
                "taux_exploitation": taux,
                "objectif": objectif,
                "objectif_atteint": exploite >= objectif
            })

        # ========================
        # CAMPAGNES
        # ========================

        campaigns = self.search([])

        is_admin = self.env.user.has_group(
            "oui_allo_rdv_pro.group_call_admin"
        )

        campagnes_data = []

        for camp in campaigns:

            camp_events = events.filtered(
                lambda e: e.campaign_id and e.campaign_id.id == camp.id
            )

            pris = len(camp_events)

            exploite = len(
                camp_events.filtered(lambda e: e.stage_id and e.stage_id.is_done)
            )

            absent = len(
                camp_events.filtered(lambda e: e.stage_id and e.stage_id.name == "Absent")
            )

            reporte = len(
                camp_events.filtered(lambda e: e.stage_id and e.stage_id.name == "Reporté")
            )

            restant = max(camp.monthly_rdv_volume - pris, 0)

            campagnes_data.append({
                "id": camp.id,
                "name": camp.name,
                "commande": camp.monthly_rdv_volume,
                "pris": pris,
                "exploite": exploite,
                "absent": absent,
                "reporte": reporte,
                "restant": restant,
                "taux_exploitation": round((exploite / pris * 100), 2) if pris else 0,
                "price_paid": camp.price if is_admin else 0,
                "start": str(camp.date_start or ""),
                "end": str(camp.date_end or ""),
            })

        # ========================
        # RDV PAR DATE
        # ========================

        rdv_by_date = []

        for ev in events:

            rdv_by_date.append({
                "id": ev.id,
                "date": str(ev.start.date()) if ev.start else "",
                "campaign": ev.campaign_id.name if ev.campaign_id else "",
                "conseiller": ev.conseiller_id.name if ev.conseiller_id else "",
                "pris": 1,
                "exploite": 1 if ev.stage_id and ev.stage_id.is_done else 0,
                "absent": 1 if ev.stage_id and ev.stage_id.name == "Absent" else 0,
                "reporte": 1 if ev.stage_id and ev.stage_id.name == "Reporté" else 0,
                "taux": 100 if ev.stage_id and ev.stage_id.is_done else 0
            })

        # ========================
        # PIE CHART
        # ========================

        pie_campaigns = [
            {"name": c["name"], "value": c["exploite"]}
            for c in campagnes_data
        ]

        pie_conseillers = [
            {"name": c["name"], "value": c["exploite"]}
            for c in conseillers_data
        ]

        bar_performance = [
            {
                "name": c["name"],
                "taux": c["taux_exploitation"]
            }
            for c in conseillers_data
        ]

        # ========================
        # EVOLUTION MENSUELLE
        # ========================

        monthly_evolution = []

        for i in range(1, 13):

            month_start = datetime(today.year, i, 1).date()

            month_end = month_start + relativedelta(months=1, days=-1)

            count = Event.search_count([
                ("start", ">=", month_start),
                ("start", "<=", month_end)
            ])

            monthly_evolution.append({
                "month": month_start.strftime("%b"),
                "value": count
            })

        # ========================
        # TOP
        # ========================

        top_campaigns = sorted(
            campagnes_data,
            key=lambda x: x["exploite"],
            reverse=True
        )[:5]

        top_conseillers = sorted(
            conseillers_data,
            key=lambda x: x["exploite"],
            reverse=True
        )[:5]

        return {

            "global": global_data,
            "today": today_data,
            "conseillers": conseillers_data,
            "campagnes": campagnes_data,
            "rdv_by_date": rdv_by_date,
            "top_campaigns": top_campaigns,
            "top_conseillers": top_conseillers,
            "pie_campaigns": pie_campaigns,
            "pie_conseillers": pie_conseillers,
            "bar_performance": bar_performance,
            "monthly_evolution": monthly_evolution,
            "is_admin": is_admin,
        }
    
    def action_open_campaigns(self):
        user = self.env.user

        domain = []

        if user.has_group('oui_allo_rdv_pro.group_call_admin'):
            domain = []

        elif user.has_group('oui_allo_rdv_pro.group_call_manager'):
            domain = [('campaign_manager_id', '=', user.id)]

        else:
            domain = [('conseiller_ids', 'in', user.id)]

        return {
            'type': 'ir.actions.act_window',
            'name': 'Campagnes',
            'res_model': 'oui.campaign',
            'view_mode': 'list,form',
            'domain': domain,
            'context': {
                'search_default_active': 1,
            }
        }
class AccountMove(models.Model):
    _inherit = 'account.move'

    campaign_id = fields.Many2one(
        'oui.campaign',
        string="Campagne"
    )