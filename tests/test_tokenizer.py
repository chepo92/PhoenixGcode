"""
Pruebas unitarias para el módulo Tokenizer de PhoenixGCode.

Ejecuta el suite de pruebas unitarias para confirmar que ambos módulos (Reader y Tokenizer) funcionan bajo contrato:
pytest tests/
"""

import pytest
from phoenixgcode.tokenizer.token import TokenType
from phoenixgcode.tokenizer.tokenizer import GCodeTokenizer


class TestGCodeTokenizer:

    @pytest.fixture
    def tokenizer(self):
        return GCodeTokenizer()

    def test_tokenize_simple_motion_command(self, tokenizer):
        """Verifica la tokenización correcta de una orden básica de movimiento con espacios."""
        line = "G1 X10.5 Y-20 E0.12 F1200"
        tokens = tokenizer.tokenize_line(line_number=1, line_text=line)

        expected_types = [
            TokenType.COMMAND_LETTER,  # G
            TokenType.COMMAND_NUMBER,  # 1
            TokenType.WHITESPACE,      # ' '
            TokenType.PARAM_LETTER,    # X
            TokenType.PARAM_VALUE,     # 10.5
            TokenType.WHITESPACE,      # ' '
            TokenType.PARAM_LETTER,    # Y
            TokenType.PARAM_VALUE,     # -20
            TokenType.WHITESPACE,      # ' '
            TokenType.PARAM_LETTER,    # E
            TokenType.PARAM_VALUE,     # 0.12
            TokenType.WHITESPACE,      # ' '
            TokenType.PARAM_LETTER,    # F
            TokenType.PARAM_VALUE,     # 1200
        ]

        assert [t.token_type for t in tokens] == expected_types
        assert "".join(t.value for t in tokens) == line
        assert all(t.line_number == 1 for t in tokens)

    def test_tokenize_preserves_whitespaces_exactly(self, tokenizer):
        """Verifica que espacios múltiples y tabulaciones sean preservados intactos."""
        line = "  G0   X5\t\tY5 "
        tokens = tokenizer.tokenize_line(line_number=5, line_text=line)

        # Reconstruir el texto uniendo los valores de cada token
        reconstructed = "".join(t.value for t in tokens)
        assert reconstructed == line

    def test_tokenize_comments(self, tokenizer):
        """Verifica la tokenización de líneas de comentarios o comentarios al final de la línea."""
        line = "M104 S200 ; Ajustar temperatura de Hotend"
        tokens = tokenizer.tokenize_line(line_number=10, line_text=line)

        comment_symbol_token = [t for t in tokens if t.token_type == TokenType.COMMENT_SYMBOL][0]
        comment_text_token = [t for t in tokens if t.token_type == TokenType.COMMENT_TEXT][0]

        assert comment_symbol_token.value == ";"
        assert comment_text_token.value == " Ajustar temperatura de Hotend"
        assert "".join(t.value for t in tokens) == line

    def test_tokenize_pure_comment_line(self, tokenizer):
        """Verifica que las líneas exclusivamente de comentarios se tokenicen correctamente."""
        line = "; --- INICIO LAYER 1 ---"
        tokens = tokenizer.tokenize_line(line_number=2, line_text=line)

        assert len(tokens) == 2
        assert tokens[0].token_type == TokenType.COMMENT_SYMBOL
        assert tokens[1].token_type == TokenType.COMMENT_TEXT
        assert tokens[1].value == " --- INICIO LAYER 1 ---"

    def test_no_command_interpretation(self, tokenizer):
        """
        Verifica que el Tokenizer NO interprete validez ni semántica.
        Líneas inválidas o comandos extraños deben tokenizarse como componentes sintácticos crudos.
        """
        line = "Z999 X--5 M10405 ABC"
        tokens = tokenizer.tokenize_line(line_number=1, line_text=line)

        # Debe generar la secuencia exacta de tokens sin lanzar excepciones
        reconstructed = "".join(t.value for t in tokens)
        assert reconstructed == line

    def test_tokenize_stream(self, tokenizer):
        """Verifica la integración con un generador de líneas (simulando la salida del Reader)."""
        input_stream = [
            (1, "; Header"),
            (2, "G21"),
            (3, "G1 X1.0 Y2.0")
        ]

        token_stream = list(tokenizer.tokenize_stream(iter(input_stream)))

        assert len(token_stream) == 3
        assert token_stream[0][0].token_type == TokenType.COMMENT_SYMBOL
        assert token_stream[1][0].token_type == TokenType.COMMAND_LETTER
        assert token_stream[1][1].token_type == TokenType.COMMAND_NUMBER