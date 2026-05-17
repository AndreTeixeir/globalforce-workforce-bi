"""
GlobalForce · Workforce Management BI
Script principal — Gerenciamento de clientes e envio de relatórios.
"""

import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.stdin.reconfigure(encoding="utf-8")

CLIENTS_FILE = os.path.join(os.path.dirname(__file__), "clients.json")


def load_clients():
    with open(CLIENTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_clients(clients):
    with open(CLIENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(clients, f, indent=2, ensure_ascii=False)


def list_clients(clients):
    if not clients:
        print("\n  Nenhum cliente cadastrado.")
        return
    print("\n  Clientes cadastrados:")
    print("  " + "-" * 55)
    for i, c in enumerate(clients, 1):
        print(f"  [{i}] {c['name']}")
        print(f"      Email:    {c.get('email', '—')}")
        print(f"      WhatsApp: {c.get('whatsapp', '—')}")
    print("  " + "-" * 55)


def add_client(clients):
    print("\n  Novo cliente")
    print("  " + "-" * 55)
    name = input("  Nome:              ").strip()
    if not name:
        print("  Nome obrigatório. Operação cancelada.")
        return
    email = input("  Email:             ").strip()
    whatsapp = input("  WhatsApp (+55...):  ").strip()
    clients.append({"name": name, "email": email, "whatsapp": whatsapp})
    save_clients(clients)
    print(f"\n  Cliente '{name}' adicionado com sucesso!")


def edit_client(clients):
    list_clients(clients)
    if not clients:
        return
    try:
        idx = int(input("\n  Número do cliente para editar: ")) - 1
        if idx < 0 or idx >= len(clients):
            print("  Número inválido.")
            return
    except ValueError:
        print("  Entrada inválida.")
        return

    c = clients[idx]
    print(f"\n  Editando: {c['name']} (Enter para manter o valor atual)")
    print("  " + "-" * 55)
    name     = input(f"  Nome [{c['name']}]: ").strip()
    email    = input(f"  Email [{c.get('email', '')}]: ").strip()
    whatsapp = input(f"  WhatsApp [{c.get('whatsapp', '')}]: ").strip()

    if name:
        c["name"] = name
    if email:
        c["email"] = email
    if whatsapp:
        c["whatsapp"] = whatsapp

    save_clients(clients)
    print(f"\n  Cliente '{c['name']}' atualizado com sucesso!")


def remove_client(clients):
    list_clients(clients)
    if not clients:
        return
    try:
        idx = int(input("\n  Número do cliente para remover: ")) - 1
        if idx < 0 or idx >= len(clients):
            print("  Número inválido.")
            return
    except ValueError:
        print("  Entrada inválida.")
        return

    name = clients[idx]["name"]
    confirm = input(f"  Confirma remover '{name}'? (s/N): ").strip().lower()
    if confirm == "s":
        clients.pop(idx)
        save_clients(clients)
        print(f"\n  Cliente '{name}' removido com sucesso!")
    else:
        print("  Operação cancelada.")


def run_reports(targets=None):
    from etl.report_generator import run_full_pipeline
    if targets:
        run_full_pipeline(clients=[c["name"] for c in targets])
    else:
        run_full_pipeline()


def select_client_for_report(clients):
    list_clients(clients)
    if not clients:
        return
    try:
        idx = int(input("\n  Número do cliente para gerar relatório: ")) - 1
        if idx < 0 or idx >= len(clients):
            print("  Número inválido.")
            return
    except ValueError:
        print("  Entrada inválida.")
        return

    selected = clients[idx]
    print(f"\n  Gerando relatório para: {selected['name']}")
    run_reports(targets=[selected])


def main():
    print("\n" + "=" * 57)
    print("   GlobalForce · Workforce Management BI")
    print("=" * 57)

    while True:
        clients = load_clients()
        print(f"\n  Clientes cadastrados: {len(clients)}")
        print("\n  ── Clientes ──────────────────────────────────")
        print("  [1] Listar clientes")
        print("  [2] Adicionar cliente")
        print("  [3] Editar cliente")
        print("  [4] Remover cliente")
        print("\n  ── Relatórios ────────────────────────────────")
        print("  [5] Gerar relatórios — Todos os clientes")
        print("  [6] Gerar relatório  — Cliente específico")
        print("\n  [0] Sair")

        opcao = input("\n  Escolha uma opção: ").strip()

        if opcao == "1":
            list_clients(clients)
        elif opcao == "2":
            add_client(clients)
        elif opcao == "3":
            edit_client(clients)
        elif opcao == "4":
            remove_client(clients)
        elif opcao == "5":
            print("\n  Iniciando pipeline para todos os clientes...")
            run_reports()
        elif opcao == "6":
            select_client_for_report(clients)
        elif opcao == "0":
            print("\n  Até logo!\n")
            break
        else:
            print("  Opção inválida.")


if __name__ == "__main__":
    main()
