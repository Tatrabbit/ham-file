# Ham File
This module can read/write ham files, and serves as the reference implementation of the format.

## Discolosure
This code was written for my personal use, it's public to make it easier to access from Colab. If it helps you for some God-forsaken reason, that's good, but just know that it's extremely sloppy and you **probably shouldn't learn from it**.

## Rationale
I needed an interchange format between multiple tools in an in-house toolkit I'm making for an AI Twitch stream. The following design principles that influenced this format are:

1. The format must be human-readable, and it must be  easy to parse.
2. It describes a linear plot, and the file must be able to be iterated, line-by-line. That is, each line should describe how to advance the output video by one unit.
3. Each tool is standalone, so they must be able to ignore data that they don't understand. Instructions were named with the ! prefix to ensure syntax checking is possible, even while meaning is abstracted.
4. Each tool should be able to output its input file, marked-up, to create a more fleshed-out version. The final tool in the chain, the "head," should write a video file. Because of this.

## Specification

HAM is an interchange format. It doesn't stand for HAM is An Interchange forMat. In fact, it doesn't stand for anything. It especially doesn't stand for all of Skinner's lies.


### At a glance

	# This is a comment
	
	# Constants:
	FOOD = grapes # I love these things!
	
	# Instructions:
	!BIG hairy monkeys
	!Things that begin with a !Bang are instructions.
	# ^ Name = "Things", Text = "that begin with...

	# Language Wart/deprecated !!
	# This special "instruction" is used as
	# a separator.
	# 
	# The next version will implement a more
	# prominent method as a language feature.
	!SCENE Home
	
	# Speech Lines in natural language:
	Caillou:
	I can't believe I got caught sneaking
	into the Chuck E. Cheeses.

	# Inline is also supported
	Boris: You are so GROUNDED, GROUNDED GROUNDED!

### Constants
Constants are specified with the format `name = value`. The name is always case-insenstiive, but fully uppercase letters are highly encouraged, pending the upcoming implementation of local constants.

Each constant must be uniquely named.

	FOO = bar
	baz = big chungus
	apples = 8
	
### Instructions
Instructions begin with a ! bang and are arbitrarily named. They are case-insensitive, and may be given arbitrary names.

Unlike constants, multiple instructions of the same name may apppear in the same file.

### Speech
Speech follows the format:
`Actor: [Stage Direction] Speech`

The bracketed `[Stage Direction]` is optional, but if it's included, it must be after the colon, and before the speech begins.