from dataclasses import dataclass, field
from typing import List, Sequence, Iterator
from phoenixgcode.model.command import Command


@dataclass(frozen=True, slots=True)
class Document:
    """
    Contenedor inmutable de la secuencia completa de comandos de un archivo G-code.
    
    Attributes:
        commands: Tupla inmutable con todos los comandos parseados en orden secuencial.
        source_path: Ruta opcional del archivo fuente original.
    """
    commands: Tuple[Command, ...] = field(default_factory=tuple)
    source_path: Optional[str] = None

    def __len__(self) -> int:
        return len(self.commands)

    def __getitem__(self, index: int) -> Command:
        return self.commands[index]

    def __iter__(self) -> Iterator[Command]:
        return iter(self.commands)