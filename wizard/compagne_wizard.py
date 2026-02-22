from datetime import timedelta

from odoo import api, fields, models


class CampaignGenerateRdvWizard(models.TransientModel):
    _name = 'campaign.generate.rdv.wizard'
    _description = 'Génération RDV depuis Campagne'

    campaign_id = fields.Many2one('oui.campaign', required=True)
    partner_id = fields.Many2one('res.partner', string="Client")
    responsable_id = fields.Many2one('res.users', string="Responsable")
    conseiller_ids = fields.Many2many(
        'res.users',
        string="Conseillers",
        domain="[('id', 'in', available_conseiller_ids)]",
    )
    available_conseiller_ids = fields.Many2many(
        'res.users',
        compute='_compute_available_conseiller_ids',
        string="Conseillers de la campagne",
    )
    rdv_line_ids = fields.One2many(
        'campaign.generate.rdv.line',
        'wizard_id',
        string="Dates RDV",
    )

    @api.depends('campaign_id', 'campaign_id.conseiller_ids')
    def _compute_available_conseiller_ids(self):
        for wizard in self:
            wizard.available_conseiller_ids = wizard.campaign_id.conseiller_ids

    @api.onchange('campaign_id')
    def _onchange_campaign_id(self):
        if self.campaign_id:
            self.conseiller_ids = self.campaign_id.conseiller_ids

    @api.onchange('conseiller_ids')
    def _onchange_conseiller_ids(self):
        for line in self.rdv_line_ids:
            line.conseiller_ids = self.conseiller_ids

    def action_generate_rdv(self):
        calendar_event_model = self.env['calendar.event']

        for line in self.rdv_line_ids:
            conseillers = line.conseiller_ids or self.conseiller_ids
            if not conseillers:
                continue

            calendar_event_model.sudo().create({
                'name': self.campaign_id.name,
                'start': line.start_datetime,
                'stop': line.start_datetime + timedelta(hours=line.duration),
                'campaign_id': self.campaign_id.id,
                'campaign_manager_id': self.responsable_id.id,
                'conseiller_id': [(6, 0, conseillers.ids)],
                'partner_id': self.partner_id.id,
                'partner_ids': [(6, 0, [self.partner_id.id])],
            })

        return {'type': 'ir.actions.act_window_close'}


class CampaignGenerateRdvLine(models.TransientModel):
    _name = 'campaign.generate.rdv.line'
    _description = 'Ligne RDV Wizard'

    wizard_id = fields.Many2one('campaign.generate.rdv.wizard')
    start_datetime = fields.Datetime("Début RDV", required=True)
    conseiller_ids = fields.Many2many(
        'res.users',
        string="Conseillers",
        domain="[('id', 'in', wizard_id.available_conseiller_ids)]",
    )
    duration = fields.Float("Durée (heures)", default=1.0)

    @api.onchange('wizard_id')
    def _onchange_wizard_id(self):
        if self.wizard_id and self.wizard_id.conseiller_ids:
            self.conseiller_ids = self.wizard_id.conseiller_ids


#  from odoo import models, fields, api,_
# from datetime import timedelta,datetime



# class CampaignGenerateRdvWizard(models.TransientModel):
#     _name = 'campaign.generate.rdv.wizard'
#     _description = 'Génération RDV depuis Campagne'

#     campaign_id = fields.Many2one('oui.campaign', required=True)
#     partner_id = fields.Many2one('res.partner', string="Client")
#     responsable_id = fields.Many2one('res.users', string="Responsable")
#     conseiller_ids = fields.Many2many('res.users', string="Conseillers")

#     rdv_line_ids = fields.One2many(
#         'campaign.generate.rdv.line',
#         'wizard_id',
#         string="Dates RDV"
#     )
    
   
    


#     def action_generate_rdv(self):
#         CalendarEvent = self.env['calendar.event']

#         for line in self.rdv_line_ids:

#             # 🎯 Conseillers à utiliser
#             conseillers = line.conseiller_ids or self.conseiller_ids

#             if not conseillers:
#                 continue

#             # Conseiller principal = premier de la liste

#             participants = []

#             # Ajouter client
#             if self.partner_id:
#                 participants.append(self.partner_id.id)

#             # Ajouter tous les conseillers comme participants
#             for conseiller in conseillers:
#                 participants.append(conseiller.id)

#             participants = list(set(participants))

#             CalendarEvent.sudo().create({
#                 'name': self.campaign_id.name,
#                 'start': line.start_datetime,
#                 'stop': line.start_datetime + timedelta(hours=line.duration),
#                 'campaign_id': self.campaign_id.id,
#                 'campaign_manager_id': self.responsable_id.id,
#                 'conseiller_id': [(6, 0, conseillers.ids)],
#                 'partner_id': self.partner_id.id,
#                 'partner_ids': [(6, 0, [self.partner_id.id])],
#             })

#         return {'type': 'ir.actions.act_window_close'}


# class CampaignGenerateRdvLine(models.TransientModel):
#     _name = 'campaign.generate.rdv.line'
#     _description = 'Ligne RDV Wizard'

#     wizard_id = fields.Many2one('campaign.generate.rdv.wizard')
#     start_datetime = fields.Datetime("Début RDV", required=True)
#     conseiller_ids = fields.Many2many(
#     'res.users',
#     string="Conseillers",
    
# )
#     duration = fields.Float("Durée (heures)", default=1.0)

#     @api.onchange('wizard_id')
#     def _onchange_wizard_id(self):
#         if self.wizard_id and self.wizard_id.conseiller_ids:
#             self.conseiller_ids = self.wizard_id.conseiller_ids



