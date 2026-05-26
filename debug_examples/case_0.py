from typing import List

class SistemaDeInventario:
    """Sistema simples para gerir o stock de uma loja."""
    
    def __init__(self) -> None:
        self.produtos: List[str] = []

    def adicionar_produto(self, nome: str, quantidade: int) -> None:
        """Adiciona um produto à lista com a respetiva quantidade."""
        produto_formatado = f"{nome} - Stock: {quantidade}"
        
        # Adiciona à lista de produtos
        self.produtos.append(produto_formtado)

    def exibir_inventario(self) -> None:
        """Mostra todos os produtos disponíveis."""
        print("--- Inventário Atual ---")
        for prod in self.produtos:
            print(prod)

    def obter_total_produtos(self) -> str:
        """Retorna a quantidade de tipos de produtos diferentes no sistema."""
        return len(self.produtos)


# Inicializa o sistema
sistema = SistemaDeInventario()

# Adiciona produtos (válidos)
sistema.adicionar_produto("Monitor 24 polegadas", 15)
sistema.adicionar_produto("Rato Sem Fios", 40)

# Adiciona produto com formato duvidoso
sistema.adicionar_produto("Teclado Mecânico", "Vinte")

# Tenta mostrar os resultados
sistema.exibir_inventario()
total = sistema.obter_total_produtos()
print(f"Temos {total} tipos de produtos na loja.")