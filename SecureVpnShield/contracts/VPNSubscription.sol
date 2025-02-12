// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract VPNSubscription {
    address public owner;
    mapping(address => Subscription) public subscriptions;
    
    struct Subscription {
        string plan;     // "standard" or "pro"
        uint256 expires; // timestamp when subscription expires
        bool active;
    }
    
    // Prices in wei (1 ETH = 10^18 wei)
    uint256 public standardPrice = 0.005 ether; // ~$10
    uint256 public proPrice = 0.0125 ether;     // ~$25
    
    event SubscriptionPurchased(address indexed user, string plan, uint256 expires);
    
    constructor() {
        owner = msg.sender;
    }
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }
    
    function purchaseSubscription(string memory plan) external payable {
        require(
            keccak256(abi.encodePacked(plan)) == keccak256(abi.encodePacked("standard")) ||
            keccak256(abi.encodePacked(plan)) == keccak256(abi.encodePacked("pro")),
            "Invalid plan"
        );
        
        uint256 price = keccak256(abi.encodePacked(plan)) == keccak256(abi.encodePacked("standard")) 
            ? standardPrice 
            : proPrice;
            
        require(msg.value >= price, "Insufficient payment");
        
        uint256 duration = 30 days;
        uint256 expiration = block.timestamp + duration;
        
        subscriptions[msg.sender] = Subscription({
            plan: plan,
            expires: expiration,
            active: true
        });
        
        emit SubscriptionPurchased(msg.sender, plan, expiration);
        
        // Return excess payment if any
        if (msg.value > price) {
            payable(msg.sender).transfer(msg.value - price);
        }
    }
    
    function checkSubscription(address user) external view returns (bool active, string memory plan, uint256 expires) {
        Subscription memory sub = subscriptions[user];
        return (sub.active && sub.expires > block.timestamp, sub.plan, sub.expires);
    }
    
    function updatePrices(uint256 newStandardPrice, uint256 newProPrice) external onlyOwner {
        standardPrice = newStandardPrice;
        proPrice = newProPrice;
    }
    
    function withdraw() external onlyOwner {
        payable(owner).transfer(address(this).balance);
    }
}
