import re
import random
token_specification = [
    ('NUMBER',      r'\d+'),                        # Integer
    ('ROLL',        r'roll\s*(\d+)d(\d+)'),         # Roll command
    ('ADV',         r'gold.adv\(\)'),                # Advantage command
    ('DISADV',      r'gold.disadv\(\)'),             # Disadvantage command
    ('QUEST',       r'quest'),                      # Method keyword
    ('COMMA',       r','),                          # Comma
    ('RECRUIT',     r'recruit'),                    # Assignment keyword
    ('SIDEQUEST',   r'sidequest'),                  # If statement
    ('JOURNEY',     r'journey'),                    # While Loop
    ('LPAREN',      r'\('),                         # Right Parentheses
    ('RPAREN',      r'\)'),                         # Left Parentheses
    ('LBRACKET',    r'{'),                          # Left Bracket
    ('RBRACKET',    r'}'),                          # Right Bracket
    ('EQUAL',       r'=='),                         # Comparison operator
    ('UNEQUAL',     r'!='),                         # Not Equal operator
    ('GREATER',     r'>'),                          # Greater than operator
    ('LESS',     r'<'),                             # Less than operator
    ('GREATEREQ',     r'>='),                       # Greater than or equal to operator
    ('LESSEQ',     r'<='),                          # Greater than or equal to operator
    ('ASSIGN',      r'='),                          # Assignment operator
    ('SCROLL',      r'scroll'),                     # Print keyword
    ('MULT',        r'powerup'),                         # Multiplication operator
    ('DIV',         r'weaken'),                          # Division operator
    ('PLUS',        r'heals'),                         # Plus operator
    ('MINUS',       r'damaged'),                          # Minus operator
    ('IDENTIFIER',  r'[A-Za-z_][A-Za-z0-9_]*'),     # Variable name
    ('SKIP',        r'[ \t\n]+'),                   # Skip over spaces and newlines
    ('MISMATCH',    r'.'),                          # Any other character (error)
]

# Combine all the regexes into one master pattern
master_pattern = '|'.join(f'(?P<{pair[0]}>{pair[1]})' for pair in token_specification)

def tokenize(code):
    line_num = 1
    for mo in re.finditer(master_pattern, code):
        kind = mo.lastgroup
        value = mo.group()
        if kind == 'SKIP':
            continue
        elif kind == 'MISMATCH':
            raise RuntimeError(f'Unexpected character {value!r} at line {line_num}')
        else:
            if kind == 'NUMBER':
                value = int(value)  # Convert to integer
            yield kind, value

class QuestInterpreter:
    def __init__(self):
        self.variables = {}
        self.quests = {}
        self.onQuest = False
        self.currQuestName = ""
        self.currQuestArgs = []
        self.questCode = []
        self.onSidequest = False
        self.onJourney = False
        self.loopBlock = []
        self.loopCondition = []
        self.skipLines = False
        self.gold = 0
        self.hasAdvantage = False
        self.hasDisadvantage = False

    def execute(self, code):
        print("Time to go on an adventure...")
        file = open(code)
        lineList = file.readlines()
        for line in lineList:
            if self.onJourney:
                self.loopBlock.append(line)
            if self.onQuest and '}' not in line:
                self.questCode.append(line)
                continue
            tokens = iter(tokenize(line))
            self.execute_block(tokens)
        print("All journeys must come to an end. Farewell!")
    
    def execute_block(self, tokens):
        # Execute a block of code (until end of line or block)
        for kind, value in tokens:
            if not self.skipLines:
                if kind == 'RECRUIT':  # Check if the token is the 'let' keyword
                    var_name_token = next(tokens)  # Get the next token (should be an identifier)
                    if var_name_token[0] != 'IDENTIFIER':  # Check if it's not an identifier
                        raise SyntaxError(f"Expected identifier after 'recruit', but got {var_name_token[1]}")
                    var_name = var_name_token[1]  # The variable name
                    assign_token = next(tokens)  # Get the next token (should be '=')
                    if assign_token[0] != 'ASSIGN':  # Check if it's not the assignment operator
                        raise SyntaxError(f"Expected '=' after variable name {var_name}, but got {assign_token[1]}")
                # Evaluate the expression after the assignment operator
                    expr_value = self.evaluate_expression(tokens,False)
                    self.variables[var_name] = expr_value  # Assign the evaluated value to the variable
                    self.gold += random.randint(1,2)
                    print(f"You recruited a new variable. You now have {self.gold} gold!")
                elif kind == 'ADV':
                    self.gold -= 10
                    print(f"You bought advantage on your next dice roll for 10 gold. You now have {self.gold} gold!")
                    self.hasAdvantage = True
                elif kind == 'DISADV':
                    self.gold -= 10
                    print(f"You bought disadvantage on your next dice roll for 10 gold. You now have {self.gold} gold!")
                    self.hasDisadvantage = True
                elif kind == 'ROLL':
                    match = re.match(r'roll\s*(\d+)d(\d+)', value)
                    if match:
                        num_dice = int(match.group(1))  # Number of dice
                        dice_type = int(match.group(2))  # Dice type
                        if num_dice * dice_type <= self.gold:
                            result = self.rollDice(num_dice, dice_type, self.hasAdvantage, self.hasDisadvantage)
                            print(f"You rolled {num_dice} {dice_type}-sided dice. You now have {self.gold} gold!")
                            self.hasAdvantage = self.hasDisadvantage = False
                        else:
                            print("Not Enough gold!")
                    else:
                        raise SyntaxError(f"Invalid roll syntax: {value}")
                elif kind == 'QUEST':  # Handle quest definition
                    quest_name_token = next(tokens)  # Quest name
                    if quest_name_token[0] != 'IDENTIFIER':
                        raise SyntaxError(f"Expected quest name after 'quest', but got {quest_name_token[1]}")
                    self.currQuestName = quest_name_token[1]
                    lparen_token = next(tokens)
                    if lparen_token[0] != 'LPAREN':
                        raise SyntaxError("Expected '(' after quest name")
                    # Parse arguments
                    while True:
                        next_token = next(tokens)
                        if next_token[0] == 'RPAREN':
                            break
                        if next_token[0] == 'IDENTIFIER':
                            self.currQuestArgs.append(next_token[1])
                        if next_token[0] == 'COMMA':
                            continue
                    lbracket_token = next(tokens)
                    if lbracket_token[0] != 'LBRACKET':
                        raise SyntaxError("Expected '{' after quest arguments")
                    self.onQuest = True
                elif kind == 'IDENTIFIER':
                    if value in self.quests:
                        # Get the arguments for the quest call
                        args = []
                        lparen_token = next(tokens)
                        if lparen_token[0] != 'LPAREN':
                            raise SyntaxError("Expected '(' after quest name")
                        while True:
                            next_token = next(tokens)
                            if next_token[0] == 'RPAREN':
                                break
                            # Collect arguments for quest call
                            if next_token[0] == 'NUMBER':
                                args.append(int(next_token[1]))
                            elif next_token[0] == 'IDENTIFIER':
                                if next_token[1] in self.variables:
                                    args.append(self.variables[next_token[1]])
                                else:
                                    args.append(next_token[1])
                            if next_token[0] == 'COMMA':
                                continue
                        # Execute the quest
                        self.execute_quest(value, args)
                    else:
                        var_name = value  # The variable name
                        if var_name not in self.variables:
                            raise SyntaxError(f"Variable {var_name} not an assigned variable or quest")
                        assign_token = next(tokens)  # Get the next token (should be '=')
                        if assign_token[0] != 'ASSIGN':  # Check if it's not the assignment operator
                            raise SyntaxError(f"Expected '=' after variable name {var_name}, but got {assign_token[1]}")
                    # Evaluate the expression after the assignment operator
                        expr_value = self.evaluate_expression(tokens,False)
                        self.variables[var_name] = expr_value  # Assign the evaluated value to the variable
                elif kind == 'SCROLL':
                    print(self.evaluate_expression(tokens,True))
                elif kind == 'SIDEQUEST':  # Handle if statement
                    # The next token should be a left parenthesis '('
                    lparen_token = next(tokens)
                    if lparen_token[0] != 'LPAREN':
                        raise SyntaxError("Expected '(' after 'sidequest'")
                    boolExpr = []
                    nextToken = next(tokens)
                    while nextToken[0] != 'RPAREN':
                        boolExpr.append(nextToken)
                        try:
                            nextToken = next(tokens)
                        except:
                            raise SyntaxError("Expected ending ')'")
                    # Evaluate the condition inside the parentheses
                    condition_value = self.evaluate_expression(boolExpr,False)
                    boolExpr.clear()
                    lbracket_token = next(tokens)
                    if lbracket_token[0] != 'LBRACKET':
                        raise SyntaxError('Expected opening bracket after condition')
                    # Check if the condition is True
                    if condition_value:
                        # Execute the block of code following the if statement
                        self.onSidequest = True
                    else:
                        self.skipLines = True
                elif kind == 'JOURNEY':
                    # The next token should be a left parenthesis '('
                    lparen_token = next(tokens)
                    if lparen_token[0] != 'LPAREN':
                        raise SyntaxError("Expected '(' after 'journey'")
                    nextToken = next(tokens)
                    while nextToken[0] != 'RPAREN':
                        self.loopCondition.append(nextToken)
                        try:
                            nextToken = next(tokens)
                        except:
                            raise SyntaxError("Expected ending ')'")
                    # Evaluate the condition inside the parentheses
                    condition_value = self.evaluate_expression(self.loopCondition,False)
                    lbracket_token = next(tokens)
                    if lbracket_token[0] != 'LBRACKET':
                        raise SyntaxError('Expected opening bracket after condition')
                    # Check if the condition is True
                    if condition_value:
                        # Execute the block of code following the if statement
                        self.onJourney = True
                    else:
                        self.skipLines = True
                        self.onJourney = False
                elif kind == 'RBRACKET':
                    if self.onQuest:
                        methodCode = []
                        for line in self.questCode:
                            lineTokens = iter(tokenize(line))
                            lineTokenList = []
                            while True:
                                try:
                                    next_token = next(lineTokens)
                                    lineTokenList.append(next_token)
                                except:
                                    methodCode.append(lineTokenList)
                                    break
                        self.quests[self.currQuestName] = {'args': self.currQuestArgs, 'code': methodCode}
                        self.onQuest = False
                        self.currQuestArgs = []
                        self.currQuestName = ""
                        self.questCode = []
                            
                    if self.onJourney:
                        while self.evaluate_expression(self.loopCondition,False):
                            for line in self.loopBlock:
                                self.execute_block(iter(tokenize(line)))
                            if not self.onJourney:
                                break
                        self.loopCondition = []
                        self.loopBlock = []
                        self.onJourney = False
                    if self.onSidequest:
                        self.onSidequest = False
                        self.gold += random.randint(1,10)
                        print(f"You completed a sidequest! You now have {self.gold} gold!")
                    self.skipLines = False

    def evaluate_expression(self, tokens, scroll):
        expr = []
        last_was_number = False  # Track if the last token was a number
    
        for kind, value in tokens:
            if kind == 'NUMBER':
                if last_was_number and not scroll:  # If two numbers are next to each other, it's an error
                    raise SyntaxError(f"Unexpected number {value} without an operator.")
                expr.append(value)
                last_was_number = True  # Mark that the last token was a number
            elif kind == 'PLUS':
                expr.append('+')
                last_was_number = False  # Reset as next token will be a number
            elif kind == 'MINUS':
                expr.append('-')
                last_was_number = False  # Reset as next token will be a number
            elif kind == 'MULT':
                expr.append('*')
                last_was_number = False  # Reset as next token will be a number
            elif kind == 'DIV':
                expr.append('/')
                last_was_number = False  # Reset as next token will be a number
            elif kind == 'LPAREN':
                if not scroll:
                    expr.append('(')
                last_was_number = False  # Reset as next token will be a number
            elif kind == 'RPAREN':
                if not scroll:
                    expr.append(')')
                last_was_number = False  # Reset as next token will be a number
            elif kind == 'GREATER':
                expr.append('>')
                last_was_number = False  # Reset as next token will be a number
            elif kind == 'LESS':
                expr.append('<')
                last_was_number = False  # Reset as next token will be a number
            elif kind == 'GREATEREQ':
                expr.append('>=')
                last_was_number = False  # Reset as next token will be a number
            elif kind == 'LESSEQ':
                expr.append('<=')
                last_was_number = False  # Reset as next token will be a number
            elif kind == 'EQUAL':
                expr.append('==')
                last_was_number = False  # Reset as next token will be a number
            elif kind == 'UNEQUAL':
                expr.append('!=')
                last_was_number = False  # Reset as next token will be a number
            elif kind == 'IDENTIFIER':
                if not scroll:
                    expr.append(str(self.variables.get(value, 0)))  # Handle variables
                else:
                    if value in self.variables:
                        expr.append(str(self.variables.get(value, 0)))  # Handle variables
                    else:
                        expr.append(value)
                last_was_number = True  # Variables are treated as numbers in expressions
            else:
                break
    
        # Join the expression parts and ensure it forms a valid string
        expr_str = ' '.join(map(str, expr))
        #if not scroll:
        #    return eval(expr_str)  # Evaluate the expression
        #else:
        #    return expr_str
        return eval(expr_str)

    def execute_quest(self, quest_name, args):
        quest_info = self.quests[quest_name]
        if len(args) != len(quest_info['args']):
            raise SyntaxError(f"Incorrect number of arguments for quest {quest_name}")
        # Create a new scope for quest variables
        local_variables = dict(zip(quest_info['args'], args))
        self.variables.update(local_variables)  # Add quest arguments to local variables
        # Execute quest code
        for lineTokens in quest_info['code']:
            self.execute_block(iter(lineTokens))  # Recursively execute quest block
        # After quest finishes, remove local variables from scope
        for arg in quest_info['args']:
            del self.variables[arg]
        self.gold += random.randint(15,30)
        print(f"You completed the quest {quest_name}! You now have {self.gold} gold!")
    
    def rollDice(self, numDice, diceType, adv, disadv):
        self.gold -= diceType * numDice
        if adv or disadv:
            roll1 = 0
            for i in range(numDice):
                roll1 += random.randint(1,diceType)
            roll2 = 0
            for i in range(numDice):
                roll2 += random.randint(1,diceType)
            if adv:
                print("Rolling with advantage!")
                if roll1 < roll2:
                    print(f"Rolling {numDice}d{diceType}: {roll1}, {roll2} --> {roll2}")
                    return roll2
                else:
                    print(f"Rolling {numDice}d{diceType}: {roll1}, {roll2} --> {roll1}")
                    return roll1
            elif disadv:
                print("Rolling with disadvantage!")
                if roll1 < roll2:
                    print(f"Rolling {numDice}d{diceType}: {roll1}, {roll2} --> {roll1}")
                    return roll1
                else:
                    print(f"Rolling {numDice}d{diceType}: {roll1}, {roll2} --> {roll2}")
                    return roll2
        else:
            sum = 0
            for i in range(numDice):
                sum += random.randint(1,diceType)
            print(f"Rolling {numDice}d{diceType}: {sum}")
            return sum

# Create an interpreter
interpreter = QuestInterpreter()

# Execute the program
interpreter.execute('code.qlang')