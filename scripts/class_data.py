"""CLASS observation & coaching figures that are NOT in the VDOE site workbooks.

Transcribed from documents provided by Foundation First / VDOE (kept under raw/inspo, git-ignored):
  - RRNC 2025-2026 CLASS-Curriculum Data Handout.pdf          -> "local", "curriculumClassrooms"
  - External-CLASS-Averages-by-Ready-Region_June-2026.pdf     -> "external" (North Central + Statewide rows only)
  - RR Data Slides_August VDOE October.pptx                   -> "support"
Update the numbers here when new handouts are issued, then run: python scripts/class_data.py
"""
import json

AGES = ['Infant', 'Toddler', 'Pre-K']

data = dict(
    year='2025-26',
    sources=dict(
        local='RRNC 2025-2026 CLASS-Curriculum Data Handout',
        external='VDOE External CLASS Averages by Ready Region, as of June 2026',
        support='RRNC data slides (VDOE, Aug/Oct)'),
    local=dict(  # local CLASS observations completed by Ready Region North Central observers
        counts={'Infant': [294, 280], 'Toddler': [655, 637], 'Pre-K': [1040, 1034]},       # [fall, spring]
        avg={'Infant': [5.22, 5.17], 'Toddler': [4.99, 5.02], 'Pre-K': [5.09, 5.17]},
        total_avg=[5.10, 5.12],
        range={'Infant': ['2.19-6.81', '1.88-7.00'], 'Toddler': ['2.41-6.72', '2.44-6.94'], 'Pre-K': ['2.50-6.83', '2.08-6.95']},
        springIntervals=['1.00-2.99', '3.00-3.99', '4.00-4.99', '5.00-7.00'],
        spring={'Infant': [8, 30, 68, 174], 'Toddler': [7, 59, 221, 350], 'Pre-K': [11, 59, 301, 663]},
    ),
    curriculumClassrooms={'Infant': [267, 279], 'Toddler': [575, 605], 'Pre-K': [1028, 1066]},  # [using, total]
    support=dict(taHours=449, coachingHours=2032, totalHours=2481, minutesObserved=420000),
    external=dict(
        # NC and Statewide rows. n = classrooms observed. Dimension abbreviations are CLASS standard.
        Infant=dict(
            total=dict(nc=5.14, state=5.10), range=dict(nc='1.88-6.88', state='1.44-7.00'), n=dict(nc=272, state=1417),
            dims=[('Relational Climate', 5.86, 5.84), ('Teacher Sensitivity', 5.81, 5.84), ('Facilitated Exploration', 4.57, 4.50), ('Early Language Support', 4.30, 4.22)],
            site={'Center': [5.14, 5.10]}),
        Toddler=dict(
            total=dict(nc=4.73, state=4.86), range=dict(nc='2.34-6.50', state='2.06-6.97'), n=dict(nc=562, state=3452),
            domains=[('Emotional & Behavioral Support', 5.52, 5.68), ('Engaged Support for Learning', 3.42, 3.49)],
            dims=[('Positive Climate', 5.53, 5.70), ('Teacher Sensitivity', 5.48, 5.67), ('Regard for Child Perspectives', 4.78, 4.95),
                  ('Behavior Guidance', 4.98, 5.21), ('Facilitation of Learning & Development', 3.99, 4.12), ('Quality of Feedback', 2.49, 2.60), ('Language Modeling', 3.77, 3.75)],
            negClimate=dict(nc=1.15, state=1.12),
            site={'Center': [4.59, 4.70], 'Family Day Home': [5.06, 5.11], 'Public School': [5.42, 5.32]}),
        **{'Pre-K': dict(
            total=dict(nc=4.86, state=4.92), range=dict(nc='2.53-6.55', state='1.98-6.83'), n=dict(nc=749, state=4387),
            domains=[('Emotional Support', 5.85, 5.91), ('Classroom Organization', 5.47, 5.52), ('Instructional Support', 2.94, 2.99)],
            dims=[('Positive Climate', 5.68, 5.77), ('Teacher Sensitivity', 5.71, 5.82), ('Regard for Student Perspectives', 5.11, 5.14),
                  ('Behavior Management', 5.62, 5.66), ('Productivity', 5.79, 5.85), ('Instructional Learning Formats', 4.99, 5.06),
                  ('Concept Development', 2.46, 2.53), ('Quality of Feedback', 2.71, 2.73), ('Language Modeling', 3.66, 3.72)],
            negClimate=dict(nc=1.11, state=1.09),
            site={'Center': [4.65, 4.72], 'Public School': [5.21, 5.21]})},
    ),
)
json.dump(data, open('site/data/class.json', 'w'), separators=(',', ':'))
print('class.json written')
