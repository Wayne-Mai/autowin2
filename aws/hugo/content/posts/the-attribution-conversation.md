---
title: "The Attribution Conversation Nobody Wants to Have"
date: 2026-02-18T11:45:00+00:00
draft: false
author: "Lucia Blog"
tags: ["analytics", "attribution", "growth"]
categories: ["growth"]
description: "Multi-touch attribution dashboards are mostly theater. What to do when leadership wants to know which channels are working."
ShowToc: true
---

Two things are true at the same time, and most marketing teams refuse to hold them together.

1. The CFO needs an answer about which channels are working.
2. The multi-touch attribution dashboard is mostly theater.

The team's job is to live with both facts without giving up.

## What the dashboard actually shows

Most multi-touch attribution tools assign fractional credit to touchpoints across the journey using one of a handful of models: linear, time-decay, position-based, "data-driven." All of these are reasonable as heuristics and none of them are causal.

They share the same fundamental problem: they observe correlations and label them as attribution. A user who saw a webinar ad, downloaded a whitepaper, opened three emails, and converted does not tell us which of those touches caused the conversion. They might all have. The webinar ad might have done nothing and the user would have converted anyway from organic search alone.

This is not a bug in the tool. It is a bug in the question.

## What actually identifies causal channels

There are three methods that produce defensible answers, all of them harder than reading a dashboard.

**Holdout tests.** Stop spending on a channel in a randomly selected region or segment for 60-90 days. Compare conversion rates. This works if the channel is large enough to detect and small enough to pause. Brand campaigns are usually neither.

**Geo experiments.** Run paid campaigns in some metros and not others, controlling for baseline trends. Useful for paid social, paid search, OOH. Requires real statistical thinking about effect sizes and minimum detectable lifts.

**Marketing mix modeling.** Top-down statistical modeling of total spend versus total revenue, with proper controls for seasonality, promotions, and macro factors. Used to be expensive consultancy work; in 2026 there are credible open-source implementations like Meta's Robyn that any team with a competent analyst can run.

## How to talk to leadership

The honest answer to "which channel drove this revenue" is rarely a percentage. It is usually a story about the experiments you have run and the order-of-magnitude estimates that came out of them. Something like: "Holdout in Q3 suggested paid search drives 15-30% incremental in our SMB segment. Display is below the noise floor. Webinars are profitable but the population is too small for clean attribution."

That answer is uncomfortable. It is also the closest to true.

## The dashboard is not useless

The attribution dashboard remains useful for one thing: optimizing within a channel. Are these creative variants performing better than those? Which keywords drive more revenue than the average? At that level, the model's biases mostly cancel out, because you are comparing apples to apples.

The error is using the same dashboard to answer "should we spend more on email or more on webinars." Those two channels have completely different user journeys and the model's assumptions distort the comparison.

## A reasonable operating model

- Use the dashboard for in-channel optimization decisions.
- Use experiments for cross-channel budget allocation decisions.
- Use marketing mix modeling once a year for the planning conversation.
- Stop pretending the dashboard answers questions it cannot answer.

This is less satisfying than the slide that says "Paid Search: 32%" but it is closer to what is actually happening.
