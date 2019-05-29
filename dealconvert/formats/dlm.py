import warnings

from . import DealFormat
from .. import dto

class DLMFormat(DealFormat):
    @property
    def suffix(self):
        return '.dlm'

    def parse_content(self, content):
        lines = [line.strip() for line in content.readlines()]
        if lines[0] != '[Document]':
            raise RuntimeError('.dlm header not detected: %s' % (lines[0]))
            sys.exit()
        fields = {}
        for line in lines[1:]:
            try:
                fields[line.split('=')[0]] = line.split('=')[1]
            except IndexError:
                warnings.warn('unable to parse .dlm line: %s' % (line))
        try:
            boards = range(int(fields['From board']), int(fields['To board'])+1)
        except (ValueError, IndexError):
            raise RuntimeError('unable to parse .dlm board number data')
        checksum = len(boards)
        if fields['Status'] == 'Show':
            checksum ^= 1
        if checksum != int(fields['Checksum']):
            warnings.warn(
                '.dlm checksum does not match: %d/%s' % (
                    checksum, fields['Checksum']))
        dealset = []
        for board in boards:
            try:
                board_str = fields['Board %02d' % (board)]
            except IndexError:
                warnings.warn('board %d not found in .dlm' % (board))
                continue
            try:
                checksum = board
                str_checksum = int(board_str[26:])
                values = []
                for char in board_str[0:26]:
                    checksum ^= ord(char)
                    value = ord(char) - 97
                    values.append(value / 4)
                    values.append(value % 4)
                if checksum != str_checksum:
                    warnings.warn(
                        '.dlm board checksum mismatch: %s (%d)' % (
                            board_str, checksum))
                deal = dto.Deal()
                deal.number = board
                deal.dealer = deal.get_dealer(board)
                deal.vulnerable = deal.get_vulnerability(board)
                for suit in range(0, 4):
                    for card in range(0, 13):
                        deal.hands[values[suit*13+card]][suit].append(
                            self.cards[card])
                dealset.append(deal)
            except:
                warnings.warn('malformed .dlm data: %s' % (board_str))
        return dealset

    def output_content(self, out_file, dealset):
        dealset = dealset[0:99]
        board_numbers = [deal.number for deal in dealset]
        first_board = min(board_numbers)
        board_count = len(dealset)
        for board in range(first_board, first_board+board_count):
            if board not in board_numbers:
                raise RuntimeError(
                    '.dlm format requires consequent board numbers')
        header = []
        header.append('[Document]')
        header.append('Headline=Generated by deal-converter.py')
        header.append('Status=Show')
        header.append('Duplicates=1')
        header.append('From board=%d' % (first_board))
        header.append('To board=%d' % (first_board+board_count-1))
        header.append('Next board to duplimate=0')
        header.append('PrintOuts=0')
        header.append('Crypto key=0')
        header.append('Checksum=%d' % (board_count^1))
        lines = ['', ''] * 99
        for i in range(1, first_board) + range(first_board+board_count, 100):
            lines[(i-1)*2] = 'Duplicates %02d=0' % (i)
            lines[(i-1)*2+1] = 'Board %02d=aaaaaabffffffkkkkkklpppppp%03d' % (
                i, i^14)
        for board in range(first_board, first_board+board_count):
            deal = dealset[board - first_board]
            lines[(board-1)*2] = 'Duplicates %02d=0' % (board)
            values = [None] * 52
            for i, hand in enumerate(deal.hands):
                for suit, cards in enumerate(hand):
                    for card in cards:
                        try:
                            values[suit*13+self.cards.index(card)] = i
                        except ValueError:
                            raise RuntimeError('invalid card: %s in board %d' % (card, board))
            line = 'Board %02d=' % (board)
            checksum = board
            for i in range(0, 26):
                value = values[i*2]*4 + values[i*2+1]
                checksum ^= 97+value
                line += chr(97+value)
            line += '%03d' % (checksum)
            lines[(board-1)*2+1] = line
        for line in header+lines:
            out_file.write(line + '\r\n')
