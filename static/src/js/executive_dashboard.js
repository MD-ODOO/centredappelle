/** @odoo-module **/

import { Component, useState, onWillStart, onPatched } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

export class ExecutiveDashboard extends Component {

    setup() {

        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.charts = {};

        this.state = useState({
            period: "month",
            loading: true,
            data: {
                global: {},
                today: {},
                conseillers: [],
                campagnes: [],
                rdv_by_date: [],
                top_campaigns: [],
                top_conseillers: [],
                pie_campaigns: [],
                pie_conseillers: [],
                bar_performance: [],
                monthly_evolution: [],
                is_admin: false,
            }
        });

        onWillStart(async () => {
            await this.loadData();
        });

        onPatched(() => {
            this.renderCharts();
        });
    }

    async loadData() {

        this.state.loading = true;

        try {

            const result = await this.orm.call(
                "oui.campaign",
                "get_executive_dashboard_data",
                [this.state.period]
            );

            this.state.data = result;

        } catch (error) {

            console.error(error);

            this.notification.add(
                "Erreur lors du chargement du dashboard",
                { type: "danger" }
            );
        }

        this.state.loading = false;
    }

    async changePeriod(ev) {

        const period = ev.target.value;

        if (this.state.period === period) return;

        this.state.period = period;

        await this.loadData();
    }

    destroyChart(name) {

        if (this.charts[name]) {
            this.charts[name].destroy();
            delete this.charts[name];
        }
    }

    renderCharts() {

        const data = this.state.data;

        if (!data) return;

        // Pie Campagnes
        const pieCampCtx = document.getElementById("pieCampaigns");

        if (pieCampCtx && data.pie_campaigns?.length) {

            this.destroyChart("pieCampaigns");

            this.charts.pieCampaigns = new Chart(pieCampCtx, {
                type: "pie",
                data: {
                    labels: data.pie_campaigns.map(d => d.name),
                    datasets: [{
                        data: data.pie_campaigns.map(d => d.value)
                    }]
                }
            });
        }

        // Pie Conseillers
        const pieConsCtx = document.getElementById("pieConseillers");

        if (pieConsCtx && data.pie_conseillers?.length) {

            this.destroyChart("pieConseillers");

            this.charts.pieConseillers = new Chart(pieConsCtx, {
                type: "pie",
                data: {
                    labels: data.pie_conseillers.map(d => d.name),
                    datasets: [{
                        data: data.pie_conseillers.map(d => d.value)
                    }]
                }
            });
        }

        // Bar Performance
        const barCtx = document.getElementById("barPerformance");

        if (barCtx && data.bar_performance?.length) {

            this.destroyChart("barPerformance");

            this.charts.barPerformance = new Chart(barCtx, {
                type: "bar",
                data: {
                    labels: data.bar_performance.map(d => d.name),
                    datasets: [{
                        label: "% Exploitation",
                        data: data.bar_performance.map(d => d.taux)
                    }]
                }
            });
        }

        // Evolution mensuelle
        const lineCtx = document.getElementById("monthlyEvolution");

        if (lineCtx && data.monthly_evolution?.length) {

            this.destroyChart("monthlyEvolution");

            this.charts.monthlyEvolution = new Chart(lineCtx, {
                type: "line",
                data: {
                    labels: data.monthly_evolution.map(d => d.month),
                    datasets: [{
                        label: "RDV",
                        data: data.monthly_evolution.map(d => d.value)
                    }]
                }
            });
        }
    }

    openConseiller(id) {

        if (!id) return;

        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "res.users",
            res_id: id,
            views: [[false, "form"]]
        });
    }

    openCampaign(id) {

        if (!id) return;

        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "oui.campaign",
            res_id: id,
            views: [[false, "form"]]
        });
    }

    getPerformanceClass(taux) {

        if (taux >= 80) return "badge-green";

        if (taux >= 50) return "badge-orange";

        return "badge-red";
    }
}

ExecutiveDashboard.template = "ExecutiveDashboard";

registry.category("actions").add(
    "executive_dashboard",
    ExecutiveDashboard
);