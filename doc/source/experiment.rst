.. currentmodule:: eelbrain

.. _experiment-class-guide:

********************************
The :class:`MneExperiment` Class
********************************

MneExperiment is a base class for managing data analysis for an MEG
experiment with MNE. Currently only gradiometer-only data is supported.

.. seealso::
    :class:`MneExperiment` class reference for details on all available methods


Summary of steps:

 * Write an experiment definition file
 * Add input files (raw fiff, MRIs)
 * Do epoch rejection for each (base) epoch and desired raw kind (see
   :ref:`MneExperiment-raw-parameter`)
 * Do analysis with desired settings

   * Reports
   * Load and inspect data manually


Defining an Experiment
======================

.. contents:: Contents
   :local:


Complete Example
----------------

The following is a complete example for an experiment class definition file
(the source file can be found in the Eelbrain examples folder at
``examples/meg/mne_experiment.py``):

.. literalinclude:: ../../examples/meg/mne_experiment.py


Basic Setup
-----------

.. py:attribute:: MneExperiment.owner

Set :attr:`MneExperiment.owner` to your email address if you want to be able to
receive notifications. Whenever you run a sequence of commands ``with
mne_experiment.notification:`` you will get an email once the respective code
has finished executing or run into an error, for example::

    >>> e = MyExperiment()
    >>> with e.notification:
    ...     e.make_report('mytest', tstart=0.1, tstop=0.3)
    ...

will send you an email as soon as the report is finished (or the program
encountered an error)


.. py:attribute:: MneExperiment.path_version

Set :attr:`MneExperiment.path_version` to ``1`` to use the current file
naming scheme (unless you defined your experiment class before Eelbrain
version 0.13 in which case you don't need to define
:attr:`MneExperiment.path_version` at all).


.. py:attribute:: MneExperiment.trigger_shift

Set this attribute to shift all trigger times by a constant (in seconds). For
example, with ``trigger_shift = 0.03`` a trigger that originally occurred
35.10 seconds into the recording will be shifted to 35.13.


Defaults
--------

.. py:attribute:: MneExperiment.defaults

The defaults dictionary needs to contain the name of the experiment,
so a minimal defaults is::

    defaults = {'experiment': 'my_experiment'}

In addition, the defaults dictionary can contain default settings for
experiment analysis parameters, e.g.::

    defaults = {'experiment': 'my_experiment',
                'epoch': 'my_epoch',
                'cov': 'noreg',
                'raw': '1-40'}


Event Variables
---------------

.. py:attribute:: MneExperiment.variables

Categorial event variables can be specified in a dictionary mapping variable
names to trigger-schemes, for example::

    class MyExperiment(MneExperiment):

        variables = {'word_type': {1: 'adjective', 2: 'noun', 3: 'verb',
                                   (4, 5, 6): 'other'}}

This defines a variable called "word_type", and on this variable all events
that have trigger 1 have the value "adjective", events with trigger 2 have
the value "noun" and events with trigger 3 have the value "verb". The last
entry shows how to map multiple trigger values to the same value, i.e. all
events that have a trigger value of either 4, 5 or 6 are labelled as "other".


Epochs
------

.. py:attribute:: MneExperiment.epochs

Epochs are specified as a {:class:`str`: :class:`dict`} dictionary. Keys are
names for epochs, and values are corresponding definitions. Epoch definitions
can use the following keys:

sel : str
    Expression which evaluates in the events Dataset to the index of the
    events included in this Epoch specification.
tmin : scalar
    Start of the epoch (default -0.1).
tmax : scalar
    End of the epoch (default 0.6).
decim : int
    Decimate the data by this factor (i.e., only keep every ``decim``'th
    sample; default 5).
baseline : tuple
    The baseline of the epoch (default ``(None, 0)``).
n_cases :
    Expected number of epochs. If n_cases is defined, a RuntimeError error
    will be raised whenever the actual number of matching events is different.
post_baseline_trigger_shift : str
    Shift the trigger (i.e., where epoch time = 0) after baseline correction.
    The value of this entry has to be the name of an event variable providing
    for each epoch the actual amount of time shift (in seconds). If the
    ``post_baseline_trigger_shift`` parameter is specified, the parameters
    ``post_baseline_trigger_shift_min`` and ``post_baseline_trigger_shift_max``
    are also needed, specifying the smallest and largest possible shift. These
    are used to crop the resulting epochs appropriately, to the region from
    ``new_tmin = epoch['tmin'] - post_baseline_trigger_shift_min`` to
    ``new_tmax = epoch['tmax'] - post_baseline_trigger_shift_max``.

A secondary epoch can be defined using a ``sel_epoch`` or ``base`` entry.
Secondary epochs inherit trial rejection from a primary epoch.
Additional parameters can be used to modify the definition, for example ``sel``
can be used to select a subset of the primary epoch. The two differ in the way
they fill in parameters that are not made explicit in the epoch's
:class:`dict`: with ``sel_epoch`` other parameters default to
:attr:`MneExperiment.epoch_defaults`, with ``base`` other parameters default to
the base epoch.

sel_epoch : str
    Name of the epoch providing primary events (e.g. whose trial rejection
    file should be used).
base : str
    Name of the epoch whose parameters provide defaults for all parameters.

Superset epochs can be defined as a dictionary with only one entry:

sub_epochs : tuple of str
    Tuple of epoch names. These epochs are combined to form the current epoch.
    The current epoch can not have any additional specification, and parameters
    from the sub_epochs must match.

Examples::

    epochs = {'noun': {'sel': "stimulus == 'noun'"},
              'noun_inanimate': {'sel_epoch': 'noun',
                                 'sel': "noun_type == 'animate'"}
              'cov': {'sel_epoch': 'noun', 'tmax': 0}}


Tests
-----

.. py:attribute:: MneExperiment.tests

The :attr:`MneExperiment.tests` dictionary defines statistical tests that
apply to the experiment's data. Each test is defined as a dictionary. The
dictionary's ``"kind"`` entry defines the test (e.g., ANOVA, related samples
T-test, ...). The other entries specify the details of the test and depend on
the test kind (see subsections on specific tests below).

kind : 'anova' | 'ttest_rel' | 't_contrast_rel'
    The test kind.
model : str
    The model which defines the cells that are used in the test. It is
    specified in the ``"x % y"`` format (like interaction definitions) where
    ``x`` and ``y`` are variables in the experiment's events.

Example::

    tests = {'my_anova': {'kind': 'anova', 'model': 'noise % word_type',
                          'x': 'noise * word_type * subject'},
             'my_ttest': {'kind': 'ttest_rel', 'model': 'noise',
                          'c1': 'a_lot_of_noise', 'c0': 'no_noise'}}


anova
^^^^^

x : str
    ANOVA model (e.g., ``"x * y * subject"``). The ANOVA model has to be fully
    specified and include ``subject``.

Example::

    tests = {'my_anova': {'kind': 'anova', 'model': 'noise % word_type',
                          'x': 'noise * word_type * subject'}}


ttest_rel
^^^^^^^^^

c1 : str | tuple
    The experimental condition. If the ``model`` is a single factor the
    condition is a :class:`str` specifying a value on that factor. If
    ``model`` is composed of several factors the cell is defined as a
    :class:`tuple` of :class:`str`, one value on each of the factors.
c0 : str | tuple
    The control condition, defined like ``c1``.
tail : int (optional)
    Tailedness of the test. ``0`` for two-tailed (default), ``1`` for upper tail
    and ``-1`` for lower tail.

Example::

    tests = {'my_ttest': {'kind': 'ttest_rel', 'model': 'noise',
                          'c1': 'a_lot_of_noise', 'c0': 'no_noise'}}


t_contrast_rel
^^^^^^^^^^^^^^

Contrasts involving different T-maps (see :class:`testnd.t_contrast_rel`)

contrast : str
    Contrast specification using cells form the specified model (see test
    documentation).
tail : int (optional)
    Tailedness of the test. ``0`` for two-tailed (default), ``1`` for upper tail
    and ``-1`` for lower tail.

Example::

    tests = {'a_b_intersection': {'kind': 't_contrast_rel', 'model': 'abc',
                                  'contrast': 'min(a > c, b > c)', 'tail': 1}}


Subject Groups
--------------

.. py:attribute:: MneExperiment.groups

Subject groups are defined in the :attr:`MneExperiment.groups` dictionary with
``{name: group_definition}`` entries. The simplest group definition is a tuple
of subject names, e.g. ``("R0026", "R0042", "R0066")``. In addition, a
group_definition can be a dictionary with the following entries:

base : str
    The name of the group to base the new group on.
exclude : tuple of str
    A list of subjects to exclude (e.g., ``("R0026", "R0042", "R0066")``)


Parcellations (:attr:`parcs`)
-----------------------------

.. py:attribute:: MneExperiment.parcs

The parcellation determines how the brain surface is divided into regions.
A number of standard parcellations are automatically defined (see
:ref:`analysis-params-parc` below). Additional parcellations can be defined in
the :attr:`MneExperiment.parcs` dictionary with ``{name: parc_definition}``
entries.

**Recombinations** of existing parcellations can be defined as dictionaries
include the following entries:

kind : 'combination'
    Has to be 'combination'.
base : str
    The name of the parcellation that provides the input labels.
labels : dict {str: str}
    New labels to create in ``{name: expression}`` format. All label names
    should be composed of alphanumeric characters (plus underline) and should not
    contain the -hemi tags.


Labels can be constructed around known **MNI coordinates** using the foillowing
entries:

kind : 'seeded'
    Has to be 'seeded'.
seeds : dict
    {name: seed(s)} dictionary, where names are strings, including -hemi tags
    (e.g., ``"mylabel-lh"``) and seed(s) are array-like, specifying one or more
    seed coordinate (shape ``(3,)`` or ``(n_seeds, 3)``).

For each seed entry, the source space vertex closest to the given MNI coordinate
will be used as actual seed, and a label will be created including all points
with a surface distance smaller than a given extent from the seed
vertex/vertices. The extent is determined when setting the parc as analysis
parameter as in ``e.set(parc="myparc-25")``, which specifies a radius of 25 mm.

For parcellations that are user-created, the following two definitions can be
used to determine how they are handled:

"subject_parc"
    Parcellations that are created outside Eelbrain for each subject. These
    parcellations are automatically generated only for scaled brains, for
    subjects' MRIs the user is responsible for creating the respective
    annot-files.
"fsaverage_parc"
    Parcellations that are defined for the fsaverage brain and should be morphed
    to every other subject's brain. These parcellations are automatically
    morphed to individual subjects' MRIs.

Example::

    parcs = {'aparc': 'subject_parc',
             'PALS_B12_Brodmann': 'fsaverage_parc',
             'lobes-op': {'kind': 'combination',
                          'base': 'lobes',
                          'labels': {'occipitoparietal': "occipital + parietal"}},
             'lobes-ot': {'kind': 'combination',
                          'base': 'lobes',
                          'labels': {'occipitotemporal': "occipital + temporal"}}}


Visualization Defaults
----------------------

.. py:attribute:: MneExperiment.brain_plot_defaults

The :attr:`MneExperiment.brain_plot_defaults` dictionary can contain options
that changes defaults for brain plots (for reports and movies). The following
options are available:

surf : 'inflated' | 'pial' | 'smoothwm' | 'sphere' | 'white'
    Freesurfer surface to use as brain geometry.
views : str | iterator of str
    View or views to show in the figure.
foreground : mayavi color
    Figure foreground color (i.e., the text color).
background : mayavi color
    Figure background color.
smoothing_steps : None | int
    Number of smoothing steps to display data.


Analysis Parameters
===================

These are parameters that can be set after an :class:`MneExperiment` has been
initialized to affect the analysis, for example::

    >>> my_experiment = MneExperiment()
    >>> my_experiment.set(raw='1-40', cov='noreg')

sets up ``my_experiment`` to use raw files filtered with a 1-40 Hz band-pass
filter, and to use sensor covariance matrices without regularization.

.. contents:: Contents
   :local:


.. _MneExperiment-raw-parameter:

raw
---

Which raw FIFF files to use.

'clm'
    The  unfiltered files (as they were added to the data, 'clm' stands for
    CALMed).
'0-40' (default)
    Low-pass filtered under 40 Hz.
'0.16-40'
    Band-pass filtered between 0.16 and 40 Hz.
'1-40'
    Band-pass filtered between 1 and 40 Hz.


group
-----

Any group defined in :attr:`MneExperiment.groups`. Will restrict the analysis
to that group of subjects.


epoch
-----

Any epoch defined in :attr:`MneExperiment.epochs`. Specify the epoch on which
the analysis should be conducted.


equalize_evoked_count
---------------------

By default, the analysis uses all epoch marked as good during rejection. Set
equalize_evoked_count='eq' to discard trials to make sure the same number of
epochs goes into each cell of the model.

'' (default)
    Use all epochs.
'eq'
    Make sure the same number of epochs is used in each cell by discarding
    epochs.


cov
---

The method for correcting the sensor covariance.

'noreg'
    Use raw covariance as estimated from the data (do not regularize).
'bestreg' (default)
    Find the regularization parameter that leads to optimal whitening of the
    baseline.
'reg'
    Use the default regularization parameter (0.1).
'auto'
    Use automatic selection of the optimal regularization method (requires
    mne-python 0.9).


inv
---

To set the inverse solution use :meth:`MneExperiment.set_inv`.


.. _analysis-params-parc:

Parcellations
-------------

The parcellation determines how the brain surface is divided into regions.
Parcellation are mainly used in tests and report generation:

 - ``parc`` or ``mask`` arguments for :meth:`MneExperiment.make_report`
 - ``parc`` argument to :meth:`MneExperiment.make_report_roi`

When source estimates are loaded, the parcellation can also be used to index
regions in the source estiomates. Predefined parcellations:

Freesurfer Parcellations
    ``aparc.a2005s``, ``aparc.a2009s``, ``aparc``, ``aparc.DKTatlas``,
    ``PALS_B12_Brodmann``, ``PALS_B12_Lobes``, ``PALS_B12_OrbitoFrontal``,
    ``PALS_B12_Visuotopic``.
``lobes``
    Modified version of ``PALS_B12_Lobes`` in which the limbic lobe is merged
    into the other 4 lobes.
``lobes-op``
    One large region encompassing occipital and parietal lobe in each
    hemisphere.
``lobes-ot``
    One large region encompassing occipital and temporal lobe in each
    hemisphere.
