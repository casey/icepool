import _context
from hdroller import Die

import cProfile
cProfile.run('Die.d12.keep_highest([12, 10, 8, 6, 4] * 10, 2)')