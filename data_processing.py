import pandas as pd

def process_games(games, username):
    """
    Process raw game data into a Pandas DataFrame suitable for analysis.
    
    This function extracts key metrics like ratings, results, and opening info,
    and enriches the data with time-based and opponent-based features.
    
    Args:
        games (list): List of game dictionaries from Lichess API.
        username (str): The username of the player to analyze (used to determine color).
        
    Returns:
        pd.DataFrame: Processed DataFrame containing one row per game.
    """
    if not games:
        return pd.DataFrame()

    processed_data = []
    
    for game in games:
        # --- Extract Basic Info ---
        game_id = game.get('id')
        variant = game.get('variant', 'standard')
        speed = game.get('speed')
        created_at = game.get('createdAt') # Timestamp in milliseconds
        
        # --- Extract Player Info ---
        white = game.get('players', {}).get('white', {})
        black = game.get('players', {}).get('black', {})
        
        white_user = white.get('user', {}).get('name', 'Unknown')
        black_user = black.get('user', {}).get('name', 'Unknown')
        
        white_rating = white.get('rating')
        black_rating = black.get('rating')
        
        # --- Determine User's Color & Stats ---
        # We need to know if the user played White or Black to calculate results correctly
        if white_user.lower() == username.lower():
            user_color = 'white'
            opponent_rating = black_rating
            user_rating = white_rating
        else:
            user_color = 'black'
            opponent_rating = white_rating
            user_rating = black_rating
            
        # --- Determine Result ---
        winner = game.get('winner') # 'white', 'black', or None (draw)
        if winner:
            if winner == user_color:
                result = 'Win'
            else:
                result = 'Loss'
        else:
            result = 'Draw'
            
        # --- Extract Opening Info ---
        opening = game.get('opening', {})
        eco = opening.get('eco') # ECO code (e.g., B01)
        opening_name = opening.get('name')
        
        # --- Calculate Move Count ---
        moves = game.get('moves', '')
        # Calculate ply (half-moves)
        ply_count = len(moves.split()) if moves else 0
        
        # --- Advanced Features (Phase 2) ---
        
        # 1. Game Termination Status
        status = game.get('status') # e.g., mate, resign, outoftime, draw
        
        # 2. Time Analysis
        # Convert timestamp to datetime object
        dt = pd.to_datetime(created_at, unit='ms')
        
        # 3. Opponent Rating Binning
        # Group opponents into rating ranges for analysis
        if opponent_rating:
            if opponent_rating < 1000: op_bin = "<1000"
            elif 1000 <= opponent_rating < 1200: op_bin = "1000-1200"
            elif 1200 <= opponent_rating < 1400: op_bin = "1200-1400"
            elif 1400 <= opponent_rating < 1600: op_bin = "1400-1600"
            elif 1600 <= opponent_rating < 1800: op_bin = "1600-1800"
            elif 1800 <= opponent_rating < 2000: op_bin = "1800-2000"
            elif 2000 <= opponent_rating < 2200: op_bin = "2000-2200"
            else: op_bin = "2200+"
        else:
            op_bin = "Unknown"

        # Append processed game to list
        processed_data.append({
            'game_id': game_id,
            'date': dt,
            'hour': dt.hour,
            'day_of_week': dt.day_name(),
            'variant': variant,
            'speed': speed,
            'user_color': user_color,
            'user_rating': user_rating,
            'opponent_rating': opponent_rating,
            'opponent_rating_bin': op_bin,
            'result': result,
            'termination': status,
            'eco': eco,
            'eco': eco,
            'opening_name': opening_name,
            'ply_count': ply_count,
            'white_user': white_user,
            'black_user': black_user,
            'white_rating': white_rating,
            'black_rating': black_rating,
            'acpl': game.get('players', {}).get(user_color, {}).get('analysis', {}).get('acpl'),
            'moves': moves,
            # Raw Data for Metrics (Time & Accuracy)
            'clocks': game.get('clocks', []),
            'clock_settings': game.get('clock', {}),
            'analysis': game.get('analysis', []),
            'white_analysis': game.get('players', {}).get('white', {}).get('analysis', {}),
            'black_analysis': game.get('players', {}).get('black', {}).get('analysis', {})
        })
        
    # Convert list of dicts to DataFrame
    df = pd.DataFrame(processed_data)
    return df

def get_opening_stats(df, color=None):
    """
    Calculate aggregate statistics for each opening played.
    
    Args:
        df (pd.DataFrame): The processed games DataFrame.
        color (str, optional): 'white' or 'black' to filter by user color.
        
    Returns:
        pd.DataFrame: DataFrame with columns [opening_name, games, wins, draws, losses, avg_rating, win_rate]
    """
    if df.empty:
        return pd.DataFrame()
        
    # Filter by color if specified
    if color:
        df = df[df['user_color'] == color]
        
    if df.empty:
        return pd.DataFrame()

    # Group by opening name and aggregate results
    stats = df.groupby('opening_name').agg(
        games=('game_id', 'count'),
        wins=('result', lambda x: (x == 'Win').sum()),
        draws=('result', lambda x: (x == 'Draw').sum()),
        losses=('result', lambda x: (x == 'Loss').sum()),
        avg_rating=('user_rating', 'mean'),
        eco=('eco', 'first')  # Take the first ECO code associated with this opening name
    ).reset_index()
    
    # Calculate Win Rate
    stats['win_rate'] = stats['wins'] / stats['games']
    
    # Sort by most played openings
    stats = stats.sort_values('games', ascending=False)
    
    return stats

def calculate_risk_metrics(df):
    """
    Calculate a 'Risk/Aggressiveness' score (1-10) based on game data.
    
    Heuristic:
    - Low Draw Rate = Higher Risk
    - Short Game Length = Higher Risk
    
    Returns:
        dict: {
            'score': float (1-10),
            'label': str,
            'feedback': str,
            'mistakes': str,
            'improvement': str
        }
    """
    if df.empty:
        return {
            'score': 0, 
            'label': "N/A", 
            'feedback': "Not enough data.",
            'mistakes': "N/A",
            'improvement': "Play more games!",
            'explanation': "Not enough data to calculate volatility."
        }
        
    # 1. Draw Rate Factor (0-10)
    # Online chess has fewer draws. We calibrate so ~10% draw rate is "Balanced" (Score 5).
    # >20% draw rate -> Score 0 (Solid)
    # <2% draw rate -> Score 9-10 (Berserker)
    total_games = len(df)
    draws = len(df[df['result'] == 'Draw'])
    draw_rate = draws / total_games if total_games > 0 else 0
    
    # Formula: (1 - (draw_rate * 5)) * 10. Clamped 0-10.
    draw_factor = max(0, (1 - (draw_rate * 5))) * 10
    
    # 2. Game Length Factor (0-10)
    # Avg 20 moves -> Score 10 (Quick kills/deaths)
    # Avg 60 moves -> Score 0 (Long grinds)
    avg_ply = df['ply_count'].mean()
    avg_moves = avg_ply / 2
    
    # Formula: (60 - avg_moves) / 4. Clamped 0-10.
    length_factor = max(0, min(10, (60 - avg_moves) / 4))
    
    # Weighted Average: 50% Draw Rate, 50% Length
    risk_score = (draw_factor * 0.5) + (length_factor * 0.5)
    risk_score = round(max(1, min(10, risk_score)), 1)
    
    # Determine Label and Feedback
    # Determine Label and Feedback based on 1-10 Score
    int_score = int(risk_score)
    
    risk_profiles = {
        1: {
            "label": "The Wall",
            "feedback": "Very hard to beat. Almost no risk.",
            "improvement": "Press harder when you're ahead."
        },
        2: {
            "label": "Safety First",
            "feedback": "Safety first. You rarely blunder.",
            "improvement": "The sharp move is often the safe one."
        },
        3: {
            "label": "Cautious Player",
            "feedback": "Solid and positional. Avoids complications.",
            "improvement": "Train calculation for forced sharp lines."
        },
        4: {
            "label": "Solid & Steady",
            "feedback": "Sound chess. Few free gifts.",
            "improvement": "Add a semi-open opening for dynamic play."
        },
        5: {
            "label": "Balanced",
            "feedback": "Good mix of solidity and aggression.",
            "improvement": "Keep it. Deepen your strategic plans."
        },
        6: {
            "label": "Calculated Risk",
            "feedback": "Takes risks, but calculated ones.",
            "improvement": "Trust intuition when you can't calculate."
        },
        7: {
            "label": "Aggressive",
            "feedback": "Hunts attacks and keeps pressure on.",
            "improvement": "Attack only when the position allows it."
        },
        8: {
            "label": "Attacker",
            "feedback": "Always pushing. Dislikes defending.",
            "improvement": "Practice defense, then counter-attack."
        },
        9: {
            "label": "Daredevil",
            "feedback": "Often sacrifices material for initiative.",
            "improvement": "Fewer sacrifices. Learn quiet moves."
        },
        10: {
            "label": "Chaos Agent",
            "feedback": "Wild games, win or lose.",
            "improvement": "Prioritize king safety and prophylaxis."
        }
    }
    
    profile = risk_profiles.get(int_score, risk_profiles[5])
    label = profile['label']
    feedback = profile['feedback']
    improvement = profile['improvement']
    mistakes = "N/A" # Deprecated in favor of specific improvement
    
    explanation = "Based on how often you draw and how quickly your games end."
        
    return {
        'score': risk_score,
        'label': label,
        'feedback': feedback,
        'mistakes': mistakes,
        'improvement': improvement,
        'explanation': explanation
    }

def calculate_pacing_metrics(df, time_control):
    """
    Calculate a 'Pacing' score (Fast/Slow/Right) based on avg game length and Time Control.
    
    Args:
        df (pd.DataFrame): Filtered dataframe.
        time_control (str): 'rapid', 'blitz', 'bullet', 'classical', or 'overall'.
        
    Returns:
        dict: { 'label': str, 'color': str, 'avg_moves': int, 'feedback': str }
    """
    if df.empty:
        return {'label': "N/A", 'color': "gray", 'avg_moves': 0, 'feedback': "No data."}
        
    avg_ply = df['ply_count'].mean()
    avg_moves = int(avg_ply / 2)
    
    # Calculate Win Rate for Context
    wins = len(df[df['result'] == 'Win'])
    total = len(df)
    win_rate = wins / total if total > 0 else 0
    
    tc = time_control.lower()
    
    # Target Moves for "Average" Pacing (Score 5.5)
    targets = {
        'bullet': 30,
        'blitz': 35,
        'rapid': 40,
        'classical': 45,
        'overall': 35
    }
    target = targets.get(tc, 35)
    
    # Calculate Pacing Score (1-10)
    # 1 = Extremely Fast, 10 = Extremely Slow
    # Scale: +/- 15 moves from target covers the full range
    diff = avg_moves - target
    # Map diff to score: -15 -> 1, +15 -> 10
    raw_score = 5.5 + (diff / 3.5)
    pacing_score = int(max(1, min(10, round(raw_score))))
    
    # Define 10 Archetypes based on Score and Win Rate
    # High Win Rate threshold
    high_wr = 0.55
    
    if pacing_score <= 2: # Extremely Fast
        if win_rate > high_wr:
            label = "Intuitive Genius"
            color = "#2BB673"
            feedback = "Instant moves, and it works."
            improvement = "Sharpen it with complex tactics."
        else:
            label = "Suicidal Sprinter"
            color = "#E07B2E"
            feedback = "Too fast, and it costs games."
            improvement = "Blunder-check before every move."
            
    elif pacing_score <= 4: # Fast
        if win_rate > high_wr:
            label = "Sharp Shooter"
            color = "#2BB673"
            feedback = "Fast and aggressive, and it pays off."
            improvement = "Pick openings that fit this style."
        else:
            label = "Impulsive Mover"
            color = "#E07B2E"
            feedback = "Rushes critical moments."
            improvement = "Slow down only in complex spots."
            
    elif pacing_score <= 6: # Average
        if win_rate > high_wr:
            label = "Balanced Pacer"
            color = "#2E9BDB"
            feedback = "Well-managed clock."
            improvement = "Next: deeper strategic plans."
        else:
            label = "Drifting Aimlessly"
            color = "#E0A43A"
            feedback = "Normal pace, but no clear plan."
            improvement = "Set a goal for each phase."
            
    elif pacing_score <= 8: # Slow
        if win_rate > high_wr:
            label = "Deep Thinker"
            color = "#2E9BDB"
            feedback = "Slow, accurate, strong calculation."
            improvement = "Use patterns to speed up easy moves."
        else:
            label = "Time Trouble Addict"
            color = "#E0A43A"
            feedback = "Thinks too long, blunders in time trouble."
            improvement = "Play simple moves fast. Save time."
            
    else: # Extremely Slow (9-10)
        if win_rate > high_wr:
            label = "Grind Master"
            color = "#2E9BDB"
            feedback = "Grinds opponents down in long endgames."
            improvement = "Polish technique with endgame studies."
        else:
            label = "Paralysis by Analysis"
            color = "#E07B2E"
            feedback = "Overthinks everything."
            improvement = "Set a time limit per move."

    return {
        'label': label,
        'color': color,
        'avg_moves': avg_moves,
        'feedback': feedback,
        'improvement': improvement,
        'score': pacing_score # Added raw score for Radar Chart
    }

import chess

def calculate_time_stats(games, username, time_control="overall", pacing_label="N/A"):
    """
    Calculate average time spent per move in Opening, Middlegame, and Endgame.
    
    Definitions:
    - Opening: Moves 1-10
    - Middlegame: Move 11+ while Queens are on board
    - Endgame: Move 11+ after Queens are traded
    
    Args:
        games (list): List of raw game dictionaries (must include 'clocks').
        username (str): User to analyze.
        time_control (str): 'rapid', 'blitz', 'bullet', 'classical', or 'overall'.
        pacing_label (str): The archetype from Pacing Analysis (e.g., "Suicidal Sprinter").
        
    Returns:
        dict: {
            'opening_avg': float, 'opening_feedback': str,
            'middlegame_avg': float, 'middlegame_feedback': str,
            'endgame_avg': float, 'endgame_feedback': str,
            'raw_times': list # Added for Histogram
        }
    """
    opening_times = []
    middlegame_times = []
    endgame_times = []
    all_times = [] # For Histogram
    
    for game in games:
        # Skip if no clock data
        if 'clocks' not in game:
            continue
            
        # Determine user color and index (White=0, Black=1)
        players = game.get('players') or {}
        white_user = players.get('white', {}).get('user', {}).get('name')
        
        if not white_user:
            white_user = game.get('white_user', 'Unknown')
            
        user_color = chess.WHITE if white_user.lower() == username.lower() else chess.BLACK
        
        # Get clocks (centiseconds)
        clocks = game.get('clocks', [])
        if not clocks:
            continue
            
        # Get increment (seconds)
        clock_settings = game.get('clock', {})
        increment = clock_settings.get('increment', 0)
        
        # Parse moves to track board state
        moves_str = game.get('moves', '')
        if not moves_str:
            continue
            
        board = chess.Board()
        moves = moves_str.split()
        
        for i, move_san in enumerate(moves):
            try:
                board.push_san(move_san)
            except ValueError:
                break
                
            is_user_move = (i % 2 == 0) if user_color == chess.WHITE else (i % 2 != 0)
            
            if is_user_move:
                if i + 2 >= len(clocks):
                    break
                    
                time_spent = (clocks[i] - clocks[i+2]) / 100 + increment
                time_spent = max(0, time_spent)
                all_times.append(time_spent)
                
                move_num = (i // 2) + 1
                
                if move_num <= 10:
                    opening_times.append(time_spent)
                else:
                    queens_on_board = len(board.pieces(chess.QUEEN, chess.WHITE)) + len(board.pieces(chess.QUEEN, chess.BLACK))
                    if queens_on_board > 0:
                        middlegame_times.append(time_spent)
                    else:
                        endgame_times.append(time_spent)

    def safe_avg(lst):
        return round(sum(lst) / len(lst), 1) if lst else 0

    op_avg = safe_avg(opening_times)
    mid_avg = safe_avg(middlegame_times)
    end_avg = safe_avg(endgame_times)
    
    # --- Generate Feedback with Pacing Synergy ---
    
    # Helper to generate phase feedback
    # Helper to generate phase feedback
    def get_feedback(phase, avg_time, target_range, pacing_label):
        low, high = target_range
        
        # Rich Advice Dictionary
        phase_advice = {
            'Opening': {
                'fast': {'reason': "Rushing openings leads to poor structures.", 'tip': "Check for tactical refutations before moving."},
                'slow': {'reason': "Over-thinking theory wastes clock.", 'tip': "Trust your prep and develop pieces naturally."},
                'good': {'reason': "You are balancing development and caution well.", 'tip': "Maintain this rhythm."}
            },
            'Middlegame': {
                'fast': {'reason': "Speed here causes tactical blunders.", 'tip': "Calculate at least 2 candidate moves in complex positions."},
                'slow': {'reason': "Time trouble will ruin your endgame.", 'tip': "Don't calculate everything; rely on patterns."},
                'good': {'reason': "You are allocating time correctly for calculations.", 'tip': "Keep looking for critical moments."}
            },
            'Endgame': {
                'fast': {'reason': "Endgames require precision, not speed.", 'tip': "Count tempos and calculate pawn races carefully."},
                'slow': {'reason': "You risk flagging in winning positions.", 'tip': "If it's theoretical, play confidently."},
                'good': {'reason': "You are navigating the technical phase well.", 'tip': "Stay alert for stalemate tricks."}
            }
        }
        
        # Base Feedback
        if avg_time < low:
            status = "Too Fast"
            base = phase_advice[phase]['fast']
        elif avg_time > high:
            status = "Too Slow"
            base = phase_advice[phase]['slow']
        else:
            status = "On Target"
            base = phase_advice[phase]['good']
            
        tip = base['tip']
            
        # Synergy: Override/Augment based on Pacing Archetype
        if "Sprinter" in pacing_label or "Impulsive" in pacing_label or "Too Fast" in pacing_label:
            if status == "On Target":
                tip += " Don't rush critical moments."
            elif status == "Too Fast":
                tip = "Double-check tactics before moving."
                
        elif "Time Trouble" in pacing_label or "Paralysis" in pacing_label or "Too Slow" in pacing_label:
            if status == "On Target":
                tip += " Good job staying on target despite your tendency to play slow."
            elif status == "Too Slow":
                tip = "Good enough beats perfect."
                
        return f"{status} · target {low}-{high}s. {tip}"

    # Define Targets based on TC
    targets = {
        'bullet': {'open': (0.5, 2), 'mid': (0.5, 3), 'end': (0.5, 3)},
        'blitz': {'open': (2, 5), 'mid': (3, 8), 'end': (3, 10)},
        'rapid': {'open': (5, 10), 'mid': (8, 20), 'end': (8, 25)},
        'classical': {'open': (10, 30), 'mid': (20, 60), 'end': (20, 90)},
        'overall': {'open': (5, 15), 'mid': (10, 30), 'end': (10, 40)}
    }
    t = targets.get(time_control.lower(), targets['overall'])
    
    return {
        'opening_avg': op_avg,
        'opening_feedback': get_feedback("Opening", op_avg, t['open'], pacing_label),
        
        'middlegame_avg': mid_avg,
        'middlegame_feedback': get_feedback("Middlegame", mid_avg, t['mid'], pacing_label),
        
        'endgame_avg': end_avg,
        'endgame_feedback': get_feedback("Endgame", end_avg, t['end'], pacing_label),
        'raw_times': all_times # Added for Histogram
    }

def get_synergized_advice(phase, score, pacing_label):
    """
    Generates specific, actionable advice based on:
    1. The Game Phase (Opening, Middlegame, Endgame)
    2. The Accuracy Score (1-10)
    3. The Player's Pacing Style (Fast vs Slow)
    """
    is_fast = "Fast" in pacing_label or "Sprinter" in pacing_label
    is_slow = "Slow" in pacing_label or "Time" in pacing_label
    
    advice = ""
    
    if phase == "Opening":
        if score <= 3:
            # Target: Level 4 (Basic Safety)
            if is_fast:
                advice = "Blitzing openings into traps. Spend 10s on moves 5-10."
            elif is_slow:
                advice = "Slow openings, bad positions. Play a simple system (London)."
            else:
                advice = "Fragile openings. Check your last 5 losses in a database."
        elif score <= 5:
            # Target: Level 6 (Competence)
            if is_fast:
                advice = "Shallow development. Put pieces on active squares."
            elif is_slow:
                advice = "Opening costs too much time. Drill your repertoire."
            else:
                advice = "Solid but passive. Learn one sharp line."
        elif score <= 7:
            # Target: Level 8 (Advanced)
            if is_fast:
                advice = "Moves known, plans missing. Study your pawn structures."
            else:
                advice = "Predictable. Add a second defense to 1.e4 or 1.d4."
        elif score <= 9:
            # Target: Level 10 (Mastery)
            advice = "Strong openings. Look for rare sidelines."
        else:
            advice = "Master-level prep. Focus on middlegame plans."

    elif phase == "Middlegame":
        if score <= 3:
            # Target: Level 4 (Safety)
            if is_fast:
                advice = "Missing one-move tactics. Check checks, captures, threats."
            elif is_slow:
                advice = "Seeing ghosts. Trust obvious recaptures."
            else:
                advice = "Tactics are the leak. Do 10 mate puzzles before playing."
        elif score <= 5:
            # Target: Level 6 (Planning)
            if is_fast:
                advice = "Attacking too early. Build a local piece majority first."
            elif is_slow:
                advice = "Missing simplifications. Trade when you're ahead."
            else:
                advice = "No plan in quiet spots. Improve your worst piece."
        elif score <= 7:
            # Target: Level 8 (Advanced Tactics/Strategy)
            advice = "Strong positional play. Study prophylaxis."
        elif score <= 9:
            # Target: Level 10 (Mastery)
            advice = "Tactically sharp. Keep sacrifices sound."
        else:
            advice = "Elite middlegame. Keep it up."

    elif phase == "Endgame":
        if score <= 3:
            # Target: Level 4 (Basics)
            if is_fast:
                advice = "Rushing endgames. Count pawn races carefully."
            elif is_slow:
                advice = "Flagging in won endings. Learn Lucena and Philidor."
            else:
                advice = "Losing won endgames. Activate your king."
        elif score <= 5:
            # Target: Level 6 (Technique)
            if is_fast:
                advice = "Drifting in equal endings. Create a passed pawn."
            elif is_slow:
                advice = "Overcalculating easy endings. Learn opposition and the square."
            else:
                advice = "Solid technique. Study rook vs pawn endings."
        elif score <= 7:
            # Target: Level 8 (Advanced)
            advice = "Excellent conversion. Study zugzwang."
        elif score <= 9:
            # Target: Level 10 (Mastery)
            advice = "Machine-like precision. Try master endgame studies."
        else:
            advice = "Tablebase-level endings."
            
    return advice

def calculate_analysis_metrics(games, username, pacing_label="Balanced"):
    """
    Calculate accuracy metrics (ACPL, Blunders) and phase breakdown from Lichess analysis data.
    """
    total_acpl = 0
    acpl_count = 0
    total_blunders = 0
    total_mistakes = 0
    total_inaccuracies = 0
    total_moves = 0
    analyzed_games = 0
    
    # Phase accumulators: [total_eval_loss, move_count, blunders]
    phases = {
        'Opening': {'loss': 0, 'moves': 0, 'blunders': 0},
        'Middlegame': {'loss': 0, 'moves': 0, 'blunders': 0},
        'Endgame': {'loss': 0, 'moves': 0, 'blunders': 0}
    }
    
    for game in games:
        if 'analysis' not in game:
            continue
            
        analyzed_games += 1
        
        # Determine user color
        # Robustly handle 'players' dict or fallback to flat fields
        players = game.get('players') or {}
        white_user = players.get('white', {}).get('user', {}).get('name')
        
        if not white_user:
            white_user = game.get('white_user', 'Unknown')
            
        user_color = chess.WHITE if white_user.lower() == username.lower() else chess.BLACK
        user_color_str = 'white' if user_color == chess.WHITE else 'black'
        
        # Overall Stats from Player Summary
        player_analysis = players.get(user_color_str, {}).get('analysis', {})
        
        # Fallback to flat analysis fields if nested not found
        if not player_analysis:
            if user_color == chess.WHITE:
                player_analysis = game.get('white_analysis', {})
            else:
                player_analysis = game.get('black_analysis', {})
                
        if player_analysis:
            # Ensure it's a dict (handle JSON string from DB)
            if isinstance(player_analysis, str):
                try:
                    import json
                    player_analysis = json.loads(player_analysis)
                except:
                    player_analysis = {}

        if player_analysis:
            total_acpl += player_analysis.get('acpl', 0)
            acpl_count += 1
            total_blunders += player_analysis.get('blunder', 0)
            total_mistakes += player_analysis.get('mistake', 0)
            total_inaccuracies += player_analysis.get('inaccuracy', 0)
            
        # Phase Breakdown from Move Analysis
        analysis = game.get('analysis', [])
        moves_san = game.get('moves', '').split()
        
        if not analysis or not moves_san:
            continue
            
        board = chess.Board()
        
        # Initialize game-specific counters
        game_blunders = 0
        game_mistakes = 0
        game_inaccuracies = 0
        
        # Iterate moves and analysis
        for i, move_san in enumerate(moves_san):
            if i >= len(analysis):
                break
                
            # Check if it's user's move
            is_user_move = (i % 2 == 0) if user_color == chess.WHITE else (i % 2 != 0)
            
            # Determine Phase
            move_num = (i // 2) + 1
            phase = 'Opening'
            if move_num > 10:
                queens = len(board.pieces(chess.QUEEN, chess.WHITE)) + len(board.pieces(chess.QUEEN, chess.BLACK))
                phase = 'Middlegame' if queens > 0 else 'Endgame'
            
            current_eval_data = analysis[i]
            prev_eval_data = analysis[i-1] if i > 0 else {'eval': 20}
            
            # The API analysis list holds evals only, so classify errors by eval drop
            if is_user_move:
                try:
                    curr = current_eval_data.get('eval', 0)
                    prev = prev_eval_data.get('eval', 0)
                    
                    loss = 0
                    if user_color == chess.WHITE:
                        if curr < prev: loss = prev - curr
                    else:
                        if curr > prev: loss = curr - prev
                            
                    loss = min(loss, 1000) # Cap at 1000
                    
                    # Classify Error
                    if loss >= 300: # Blunder threshold
                        phases[phase]['blunders'] += 1
                        game_blunders += 1
                    elif loss >= 100:
                        game_mistakes += 1
                    elif loss >= 50:
                        game_inaccuracies += 1
                        
                    phases[phase]['loss'] += loss
                    phases[phase]['moves'] += 1
                    
                except Exception:
                    pass
            
            try:
                board.push_san(move_san)
            except:
                break
                
            total_moves += 1 if is_user_move else 0

        # Update Totals (Use manual counts if API data missing)
        if player_analysis and player_analysis.get('blunder') is not None:
            total_blunders += player_analysis.get('blunder', 0)
            total_mistakes += player_analysis.get('mistake', 0)
            total_inaccuracies += player_analysis.get('inaccuracy', 0)
        else:
            total_blunders += game_blunders
            total_mistakes += game_mistakes
            total_inaccuracies += game_inaccuracies

    if acpl_count == 0:
        return None
        
    # Calculate Phase Scores (1-10)
    def get_score(avg_loss):
        if avg_loss == 0: return 0
        if avg_loss < 15: return 10
        if avg_loss < 25: return 9
        if avg_loss < 35: return 8
        if avg_loss < 45: return 7
        if avg_loss < 55: return 6
        if avg_loss < 65: return 5
        if avg_loss < 75: return 4
        if avg_loss < 90: return 3
        if avg_loss < 110: return 2
        return 1

    phase_stats = {}
    for p, data in phases.items():
        moves = data['moves']
        avg_loss = data['loss'] / moves if moves > 0 else 0
        blunders = data['blunders']
        
        score = get_score(avg_loss)
        
        # Metrics
        accuracy_percent = max(0, round(100 - (avg_loss / 1.5), 1)) # Heuristic: 150 ACPL = 0% acc
        blunder_rate = round((blunders / moves) * 100, 1) if moves > 0 else 0.0
        
        # Sophisticated Advice Generation
        advice = get_synergized_advice(p, score, pacing_label)
            
        phase_stats[p] = {
            'avg_loss': round(avg_loss, 1), 
            'score': score,
            'accuracy_percent': accuracy_percent,
            'blunder_rate': blunder_rate,
            'advice': advice
        }

    return {
        'games_analyzed': analyzed_games,
        'avg_acpl': round(total_acpl / acpl_count, 1),
        'blunder_rate': round((total_blunders / total_moves) * 100, 1) if total_moves > 0 else 0,
        'mistake_rate': round((total_mistakes / total_moves) * 100, 1) if total_moves > 0 else 0,
        'inaccuracy_rate': round((total_inaccuracies / total_moves) * 100, 1) if total_moves > 0 else 0,
        'phases': phase_stats
    }
