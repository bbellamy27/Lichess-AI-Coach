import os
import platform
import shutil

import chess
from stockfish import Stockfish


class LocalEngine:
    def __init__(self, path=None):
        if path is None:
            # Auto-detect default path based on OS
            if platform.system() == "Windows":
                self.path = "stockfish.exe"
            elif not shutil.which("stockfish") and os.path.exists("./stockfish"):
                self.path = "./stockfish"
            else:
                self.path = "stockfish"
        else:
            self.path = path

        self.engine = None

    def _init_engine(self):
        # Absolute path: Windows won't launch a relative executable path from subprocess
        here = os.path.join(os.path.dirname(os.path.abspath(__file__)), self.path)
        path = shutil.which(self.path) or next(
            (os.path.abspath(p) for p in (self.path, here) if os.path.isfile(p)), None)
        if not path:
            raise FileNotFoundError("Stockfish executable not found. Please install Stockfish and ensure it is "
                                    "in your PATH or the project directory.")

        # Initialize Stockfish with reasonable settings for quick analysis
        self.engine = Stockfish(path=path, depth=15, parameters={"Threads": 2, "Hash": 16})

    def _eval(self, board):
        """Centipawn eval for the side to move, with mates capped at +/-1000."""
        self.engine.set_fen_position(board.fen())
        top_moves = self.engine.get_top_moves(1)
        if not top_moves:
            return 0
        info = top_moves[0]
        if info.get('Mate') is not None:
            return 1000 if info['Mate'] > 0 else -1000
        return max(-1000, min(1000, int(info.get('Centipawn', 0))))

    def analyze_game(self, moves_san):
        """
        Analyze a game and calculate ACPL.

        Args:
            moves_san (list): List of moves in SAN format.

        Returns:
            dict: {'white_acpl': float, 'black_acpl': float, 'analysis': [{'eval': int}, ...]}
        """
        if not self.engine:
            self._init_engine()

        losses = {chess.WHITE: 0, chess.BLACK: 0}
        moves = {chess.WHITE: 0, chess.BLACK: 0}
        analysis_list = []
        board = chess.Board()

        for move_san in moves_san:
            mover = board.turn
            score_before = self._eval(board)
            try:
                board.push_san(move_san)
            except ValueError:
                break
            score_after = self._eval(board)

            # Evals are relative to the side to move, so after the move the sign flips:
            # loss = before - (-after) = before + after
            losses[mover] += max(0, score_before + score_after)
            moves[mover] += 1

            # Store analysis data in Lichess format (always White's perspective)
            analysis_list.append({'eval': -score_after if mover == chess.WHITE else score_after})

        return {
            'white_acpl': losses[chess.WHITE] / moves[chess.WHITE] if moves[chess.WHITE] else 0,
            'black_acpl': losses[chess.BLACK] / moves[chess.BLACK] if moves[chess.BLACK] else 0,
            'analysis': analysis_list,
        }
