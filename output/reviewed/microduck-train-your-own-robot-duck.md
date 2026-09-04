---
title: "Microduck 机器鸭：可爱之外，开放玩法才是更大的吸引力"
slug: "microduck-train-your-own-robot-duck"
summary: "对比 Loona、aibo、Petoi 与 Reachy Mini，看看 Microduck 除了外形可爱，还有什么独到之处。"
read_minutes: 5
tags: "消费机器人 / 开放生态 / 用户共创"
review_status: "approved"
reviewed_at: "2026-09-04"
generated_at: "2026-09-04"
---

# Microduck 机器鸭：可爱之外，开放玩法才是更大的吸引力

> 对比 Loona、aibo、Petoi 与 Reachy Mini，看看 Microduck 除了外形可爱，还有什么独到之处。

## 一句话看懂

一看到 Microduck 有趣的形象，我就被它吸引了。进一步了解后，我发现用户还能够在模拟环境中训练它，再把训练好的动作部署到机器鸭上，与其他人分享。**最让我期待的是，拿到这只机器鸭之后，还能通过后续训练或使用社区分享的成果，让它不断学会新的动作。** 就算不亲自开发，我也会期待看看别人又想出了什么有意思的玩法。比起一个什么都会的助手，我更想拥有这样一个能和大家一起探索、一起折腾的小伙伴。

## 核心体验

第一次看 Microduck 的演示，我就觉得它有点笨拙的样子很有意思：会叫、会摔倒，也会滑行。我能明显看出它身上的机械结构，却又觉得它像个有性格的小家伙，很像《机器人总动员》或其他电影里的机器人角色。**比起做得像一只真实的动物，我更喜欢这种带着机械感的可爱。**

我也进一步查了它是怎么学习新动作的。官方开放了控制、仿真、强化学习和实机部署的软件，用户可以先在模拟环境中训练，再把训练好的行为放到机器人上运行。当然，不是说对着鸭子说一句话，它就会自动学会新技能，而是需要使用相应的开发工具才能完成训练。如果暂时不想写代码，也可以先体验它自带的动作。[官方产品说明](https://pollen-robotics.com/microduck/)

为了进一步理解 Microduck 的独特性，我又比较了几款相似的机器人产品，也把同品牌的 Reachy Mini 放在一起看了看。

| 产品 | 它先用什么吸引用户 | 用户能参与到哪一步 |
| --- | --- | --- |
| Microduck | 机械感与可爱并存的鸭子形象，强调动作和玩耍 | 开放控制、仿真与强化学习软件，可重新训练运动策略 |
| Loona | 丰富表情与互动游戏，偏机器宠物体验 | 提供 Blockly 图形化编程，并非只能玩预设游戏 |
| Sony aibo | 宠物式互动与逐渐形成偏好的养成感 | 提供 Web API 和可视化动作编程，不等于开放底层训练系统 |
| Petoi Bittle / Nybble | 机器狗、机器猫形态，突出编程学习与动手改造 | 基于 OpenCat，可用图形化工具、Python、C++ 开发与扩展 |
| Reachy Mini | 天线和眼睛形成的角色感，突出桌面交互 | 开放 SDK，可安装社区应用，也可接入自己的 Agent |

能力来源：[Microduck](https://pollen-robotics.com/microduck/) · [Loona](https://keyirobot.com/pages/loonadetail?isRedirect=true&kol=es_erensenar) · [aibo](https://us.aibo.com/developer/) · [Petoi](https://www.petoi.com/pages/about) · [Reachy Mini](https://huggingface.co/docs/reachy_mini/index)。

我觉得 Loona 和 aibo 的外形也很讨喜，而且它们都允许用户自定义一些行为。Petoi 在编程和扩展方面做得很深入，只是看到它的外形和介绍，我更容易把它当作学习机器人知识的工具。当然，这是个人观感，不代表它只面向高校及学生群体。

我也很喜欢 Reachy Mini 的两只天线和一大一小的眼睛。不过，要开始使用它，通常得先花两三小时组装，再完成连接和设置。我还看到网上有人给它接入 Hermes，让它读取记忆、调用工具来帮自己做事，但这属于需要额外配置的进阶玩法。Microduck 则不一样，它主要用叫声和动作交流，不说人话。在我看来，这反而更像一个能陪人玩耍的小伙伴。[Reachy Mini 入门指南](https://huggingface.co/docs/reachy_mini/platforms/reachy_mini/get_started)、[Hermes 社区集成示例](https://github.com/Timverhoogt/reachy-mini-hermes)、[Microduck 设计说明](https://pollen-robotics.com/microduck/blog/introducing-microduck/)

## 为什么有效

这让我想到《塞尔达》那种开放探索的乐趣：除了完成任务，还能看到别人发明的新奇玩法，自己也想跟着试一试。机器人和游戏当然不同，但对我来说，这种期待很相似。如果机器人自带的功能已经足够有趣，用户又能在此基础上继续尝试，那我们能体验到的东西，就不必局限于厂商最初的设计。

**不是每个人都要会开发，但通过社区里的开源分享，大家都有机会不断体验到新的东西。** 一个用户做出的动作，其他人可以直接尝试，也可以在此基础上继续修改，不必每次都从头开始。在我看来，Hugging Face 的机会不只在于向更广泛的人群售卖机器人，还在于让用户彼此交流、分享成果，一起把机器人的用途和玩法丰富起来。Microduck 团队也希望大家一起分享行为、训练环境和复现方法。[官方社区愿景](https://pollen-robotics.com/microduck/blog/introducing-microduck/)

## 问题与边界

**代码开源了，不等于普通用户就能轻松用起来。** 想自己训练，得准备工具和算力，也要花时间调试；想用别人的成果，则要确认版本是否兼容、运行是否安全，出问题后能不能恢复。即便看到别人用得很顺畅，自己也可能一直卡在安装和配置上，时间一长，兴趣就容易被消磨掉。Reachy Mini 已经提供了安装社区应用的入口，这也是 Microduck 可以借鉴的方向：让用户找到感兴趣的内容后，能更方便地用到自己的机器人上。[Reachy Mini 应用入口](https://huggingface.co/docs/reachy_mini/index)

当然，我觉得它笨拙可爱，不代表我能接受它频繁故障或不受控制。偶尔的小失误可能让人觉得有趣，但基本体验还是要可靠。它的首发确实很受关注：报道援引公司说法，首个 24 小时订单超过 260 万美元，新增订单当时预计要等四至六个月。这是预售阶段的成绩，后续更值得关注的是交付后的使用体验。[首发订单报道，2026 年 8 月 28 日](https://www.businessinsider.com/hugging-faces-duck-robot-hits-sales-roller-skate-2026-8)

## 我的判断

**我觉得 Microduck 有意思的地方，是它让人想亲自上手尝试，把自己的想法变成看得见的动作和互动。** 有人单纯喜欢它的样子，有人想训练它做点新动作，也有人好奇社区里还会出现什么新的创意。这样一来，它就有可能吸引不同兴趣的人。

如果从产品设计的角度看，我更想知道：不想写代码的人能不能获得有趣的体验？想改一点东西的人会不会无从下手？愿意深入折腾的人，又有多大空间去尝试自己的想法？比起社区里发布了多少代码和视频，我更关心别人能不能把这些成果用起来，以及过了一段时间，大家还愿不愿意继续使用、尝试新的内容。

## 可迁移的方法

1. **先让用户初步用起来，再由他决定要不要深入探索。** 对有技术门槛的产品，最好先让人感受到乐趣，而不是要求用户学完一套工具，才能开始体验。
2. 为不同用户群体提供不同深度的体验入口。直接使用、简单修改和深入开发，不必走同一条路径。想改一个动作的人，不应该先被要求学会整套开发流程。
3. 把分享要求说清楚，让别人更容易复现。社区可以提供发布模板和检查指引，帮助作者说明适用设备与版本、安装步骤、测试情况，以及出问题后的恢复方法。这样，其他用户不必从头摸索，也更容易判断作品是否适合自己。分享的目标不只是展示成果，还要让别人能够复现和使用。

## 产品启示

我不需要这只机器鸭一开始就什么都会。我更期待的是，现在能开箱即玩，过一阵子还能发现新的玩法，甚至自己也能参与做点什么。对这类 AI 产品来说，允许用户修改只是第一步；更有意义的是，一个人想出来的好点子，其他人也能用上，并在此基础上继续尝试。

## 信息来源

*备注：本文基于演示视频、官方资料及开源代码调研，结合个人观察写成，未进行实机测试。*

官方介绍与开发资料：[Microduck](https://pollen-robotics.com/microduck/) · [控制软件](https://github.com/pollen-robotics/microduck) · [训练工具](https://github.com/pollen-robotics/microduck_rl) · [Loona](https://keyirobot.com/pages/loonadetail?isRedirect=true&kol=es_erensenar) · [aibo](https://us.aibo.com/developer/) · [Petoi](https://www.petoi.com/pages/about) · [Reachy Mini](https://huggingface.co/docs/reachy_mini/index)。

社区与新闻资料：[Reachy Mini–Hermes 集成](https://github.com/Timverhoogt/reachy-mini-hermes) · [Business Insider 首发订单报道](https://www.businessinsider.com/hugging-faces-duck-robot-hits-sales-roller-skate-2026-8)。资料核对日期：2026 年 9 月 4 日。
