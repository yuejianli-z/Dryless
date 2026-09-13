"""Shared behavioral contract; simulated time is not a live 20-minute test."""
import unittest
from microbreak import MicrobreakController

def feed(controller, start, end, face=True):
    for second in range(start, end + 1):
        result = controller.update(face, second)
    return result

class MicrobreakContract(unittest.TestCase):
    def test_trigger_hold_end_and_next_cycle(self):
        c = MicrobreakController()
        self.assertFalse(feed(c, 0, 1199)['active'])
        self.assertTrue(c.update(True, 1200)['started'])
        self.assertTrue(feed(c, 1201, 1229)['active'])
        self.assertTrue(c.update(True, 1230)['ended'])
        self.assertFalse(feed(c, 1231, 2429)['active'])
        self.assertTrue(c.update(True, 2430)['started'])

    def test_twenty_seconds_away_dismisses(self):
        c = MicrobreakController()
        feed(c, 0, 1200)
        self.assertTrue(feed(c, 1201, 1219, False)['active'])
        self.assertTrue(c.update(False, 1220)['ended'])

    def test_brief_loss_is_not_added_and_long_loss_resets(self):
        c = MicrobreakController()
        feed(c, 0, 1000)
        feed(c, 1001, 1003, False)
        c.update(True, 1004)
        self.assertEqual(c.presence, 1000)
        feed(c, 1005, 1010, False)
        c.update(True, 1011)
        self.assertEqual(c.presence, 0)

    def test_sleep_or_pause_cannot_instantly_trigger(self):
        c = MicrobreakController()
        feed(c, 0, 1199)
        self.assertFalse(c.update(True, 1700)['active'])
        self.assertEqual(c.presence, 0)
        feed(c, 1701, 1720)
        c.update(True, 1721, paused=True)
        self.assertEqual(c.presence, 0)
        self.assertFalse(c.previous_face)

if __name__ == '__main__':
    unittest.main()
