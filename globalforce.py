"""
GlobalForce · Workforce Management BI
Script principal — Gerenciamento de clientes e envio de relatórios.
"""

import sys

import clients_store

sys.stdout.reconfigure(encoding="utf-8")
sys.stdin.reconfigure(encoding="utf-8")


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
    clients_store.add_client(name, email, whatsapp)
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

    fields = {}
    if name:
        fields["name"] = name
    if email:
        fields["email"] = email
    if whatsapp:
        fields["whatsapp"] = whatsapp

    updated = clients_store.update_client(c["id"], fields)
    if updated is None:
        print("  Cliente não encontrado (removido em outra sessão?).")
        return
    print(f"\n  Cliente '{updated['name']}' atualizado com sucesso!")


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
        if clients_store.delete_client(clients[idx]["id"]):
            print(f"\n  Cliente '{name}' removido com sucesso!")
        else:
            print("  Cliente não encontrado (removido em outra sessão?).")
    else:
        print("  Operação cancelada.")


def run_reports(targets=None):
    from etl.report_generator import run_full_pipeline
    run_full_pipeline(targets if targets else clients_store.load_clients())


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
        clients = clients_store.load_clients()
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
