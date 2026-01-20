# PrecisionAlignment

In this repository we provide a faithful implementation for computing precision of Petri nets with respect to an event log, following the approach proposed in the paper "[Measuring precision of modeled behavior](https://link.springer.com/article/10.1007/s10257-014-0234-7)".

## Use of code
Integration with Pm4py

## Computing precision
The steps for computing the precision are:
1) compute one optimal alignment for each trace in the log, $\Lambda$ is the set of alignments;
2) project the alignment to moves on model and synchronous moves only to obtain a fully compliant sequence of activities, $\bar \Lambda$ is the set of projected alignments;
3) build the automaton $A$ considering all the prefixes for the sequences in the projected alignments $\bar \Lambda$ as states;
4) compute weight for each state of the automaton $\omega(s) = \sum_{\forall \gamma \in \bar \Lambda} \omega(\gamma)$, where $\omega(\gamma)$ is the frequence of a sequence in $\bar \Lambda$;
5) For each state, compute the set of its available actions, i.e. possible direct successor activities according to the model ($a_v$) and them compare it with the set of executed actions, i.e. activities really executed in the traces ($e_v$);
6) Compute precision for automaton $A$ as follows:  $a_p = \frac{\sum_{s}\omega (s) \cdot |e_x(s)|}{\sum_{s}\omega (s) \cdot |a_v(s)|}$.

We refer to the paper for additional details.

### Example
For example, consider the following process model, log and projected alignments.

| Process Model| Event log and alignments|
| :---: | :---: |
|<img src="https://github.com/chiaragii/PrecisionAlignment/blob/main/example/model_example.png" width="400"> | <img src="https://github.com/chiaragii/PrecisionAlignment/blob/main/example/log_example.png" width="400"> | 

The corresponding automaton is:

<p align="center">
<img src="https://github.com/chiaragii/PrecisionAlignment/blob/main/example/automaton_example.png" width="500">
</p>

therefore, $a_p = \frac{5⋅1 + 5⋅3 + 2⋅2 + 1⋅1 +1⋅1 +1⋅1 +1⋅1 +1⋅1 +1⋅1 +2⋅1 +2⋅1}{5⋅1 + 5⋅3 + 2⋅2 + 1⋅3 +1⋅2 +1⋅3 +1⋅3 +1⋅1 +1⋅3 +2⋅1 +2⋅1} = \frac{34}{43} = 0.79$
