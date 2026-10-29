import os
import time
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rtde_receive import RTDEReceiveInterface

# Configuração de IP do URSim / Robô
IP_UR = "127.0.0.1"

# Nomes das Juntas
JOINT_NAMES = [
    "J1 (Base)",
    "J2 (Shoulder)",
    "J3 (Elbow)",
    "J4 (Wrist 1)",
    "J5 (Wrist 2)",
    "J6 (Wrist 3)"
]

# Mapeamento dos inteiros do JointMode para texto descritivo
JOINT_MODE_MAP = {
    235: "RESET",
    236: "SHUTDOWN",
    238: "FREEDRIVE",
    239: "POWER_OFF",
    245: "NO_RESPONSE",
    246: "INIT",
    247: "BOOTING",
    252: "FAULT",
    253: "RUNNING",
    255: "IDLE"
}

def get_mode_description(code):
    """Retorna o inteiro formatado junto com a descrição correspondente."""
    if code is None:
        return "N/A"
    desc = JOINT_MODE_MAP.get(int(code), "UNKNOWN")
    return f"{int(code)} ({desc})"

def generate_dashboard(temp, torque, current, joint_modes) -> Table:
    """Gera a tabela formatada com os dados e o estado das 6 juntas."""
    table = Table(show_header=True, header_style="bold cyan", expand=True)
    
    # Coluna de Métrica
    table.add_column("Métrica", style="bold white", width=15)
    
    # Colunas para cada uma das 6 Juntas
    for name in JOINT_NAMES:
        table.add_column(name, justify="center")

    # Linha 1: Estado da Junta (Inteiro + Descrição)
    mode_row = [get_mode_description(m) for m in joint_modes]
    table.add_row("Joint Mode", *mode_row)

    # Linha 2: Temperatura (°C)
    temp_row = [f"{t:.1f} °C" if t is not None else "N/A" for t in temp]
    table.add_row("Temperature", *temp_row)

    # Linha 3: Torque (Nm)
    torque_row = [f"{t:.2f} Nm" if t is not None else "N/A" for t in torque]
    table.add_row("Torque", *torque_row)

    # Linha 4: Corrente Real (A)
    current_row = [f"{c:.2f} A" if c is not None else "N/A" for c in current]
    table.add_row("Current", *current_row)

    return table

def main():
    console = Console()
    console.print(f"[bold yellow]Connecting to UR Robot RTDE at {IP_UR}...[/bold yellow]")

    try:
        rtde_r = RTDEReceiveInterface(IP_UR)
    except Exception as e:
        console.print(f"[bold red][ERRO] Fail to connect RTDE: {e}[/bold red]")
        return

    console.print("[bold green]RTDE Connected successfully![/bold green]")
    time.sleep(1)

    # Renderização em tempo real (Live Loop)
    with Live(refresh_per_second=10, console=console) as live:
        try:
            while rtde_r.isConnected():
                # Leitura das métricas via RTDE
                joint_modes = rtde_r.getJointMode()     # Retorna lista de 6 inteiros
                temp = rtde_r.getJointTemperatures()   # Retorna lista de 6 floats
                torque = rtde_r.getTargetMoment()      # Retorna lista de 6 floats
                current = rtde_r.getActualCurrent()     # Retorna lista de 6 floats

                # Montagem da tabela
                table = generate_dashboard(temp, torque, current, joint_modes)
                panel = Panel(
                    table,
                    title="[bold green]UR10 - Dashboard Telemetria + Estado de Juntas[/bold green]",
                    subtitle="[dim]Pressione CTRL+C para sair[/dim]"
                )

                live.update(panel)
                time.sleep(0.1)

        except KeyboardInterrupt:
            console.print("\n[yellow]Monitoramento encerrado pelo usuário.[/yellow]")
        finally:
            rtde_r.disconnect()

if __name__ == "__main__":
    main()