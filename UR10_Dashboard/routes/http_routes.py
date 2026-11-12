"""
Rotas HTTP: as páginas do dashboard e a API usada pelos botões.

Páginas:
    /           tela inicial
    /monitor    telemetria (cards, gráficos, Fault History, logs)
    /config     limites de segurança

API:
    GET  /api/status            estado da conexão com o robô
    POST /api/control/<ação>    play, pause ou stop no programa do robô
    GET  /api/thresholds        limites atuais
    POST /api/thresholds        salva novos limites
"""

import logging

from flask import jsonify, render_template, request

log = logging.getLogger("routes")


def register_routes(app, robot, alarms, robot_ip, frontend_config):
    """Cadastra todas as rotas HTTP no app Flask."""

    # Variáveis disponíveis em todos os templates HTML
    @app.context_processor
    def template_variables():
        return {"ip": robot_ip, "frontend_config": frontend_config}

    # ------------------------------------------------------------------
    # Páginas
    # ------------------------------------------------------------------

    @app.route("/")
    def home_page():
        return render_template("home.html")

    @app.route("/monitor")
    def monitor_page():
        return render_template("monitor.html")

    @app.route("/config")
    def config_page():
        return render_template("config.html")

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------

    @app.route("/api/status")
    def get_status():
        return jsonify(robot.status())

    @app.route("/api/control/<action>", methods=["POST"])
    def control_robot(action):
        try:
            robot.send_command(action)
        except ValueError as error:  # ação que não existe
            return jsonify({"status": "error", "message": str(error)}), 400
        except Exception as error:   # robô não respondeu
            log.error("Erro ao executar o comando %s: %s", action, error)
            return jsonify({"status": "error", "message": str(error)}), 500

        return jsonify({"status": "ok", "action": action})

    @app.route("/api/thresholds", methods=["GET"])
    def get_thresholds():
        return jsonify(alarms.config)

    @app.route("/api/thresholds", methods=["POST"])
    def save_thresholds():
        try:
            alarms.save(request.get_json(force=True))
        except (ValueError, TypeError) as error:
            return jsonify({"status": "error", "message": str(error)}), 400

        return jsonify({"status": "ok"})
