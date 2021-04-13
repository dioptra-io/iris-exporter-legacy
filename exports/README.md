Column | Type | Comments
-------|------|---------
`probe_src_addr`    | IPv6
`probe_dst_addr`    | IPv6
`probe_src_port`    | UInt16
`probe_dst_port`    | UInt16
`probe_ttl_l3`      | UInt8
`probe_ttl_l4`      | UInt8
`reply_src_addr`    | IPv6
`reply_protocol`    | UInt8 | 1 for ICMP, 58 for ICMPv6
`reply_icmp_type`   | UInt8 | 11 for ICMP Time Exceed, 3 for ICMPv6 Time Exceeded
`reply_icmp_code`   | UInt8
`reply_ttl`         | UInt8
`reply_size`        | UInt16
`reply_mpls_labels` | Array(UInt32)
`rtt`               | Float64
`round`             | UInt8
