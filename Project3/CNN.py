import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

class CNN(nn.Module):
    def __init__(self, size, alpha=0.01, epochs=10, activation='ReLU', optimizer='Adam'):
        super(CNN, self).__init__()
        self.size = size
        self.alpha = alpha
        self.epochs = epochs
        self.conv = nn.Sequential(
            nn.Conv2d(1,6,2),
            nn.ReLU(),
            nn.Conv2d(6,12,2),
            nn.ReLU())
        self.policy = nn.Sequential(
            nn.Linear(12*(self.size-2)**2+1,120),
            self.__choose_activation_fn(activation),
            nn.Linear(120,84),
            self.__choose_activation_fn(activation),
            nn.Linear(84,self.size**2),
            nn.Softmax(dim=1))

        params = list(self.parameters())
        self.optimizer = self.__choose_optimizer(params, optimizer)
        self.loss_fn = nn.BCELoss()

    def forward(self, x, training=False):
        self.train(training)
        x1, x2 = self.transform_input(x)
        x2 = self.conv(x2)
        x2 = x2.reshape(-1,12*(self.size-2)**2)
        x = torch.cat((x1,x2), dim=1)
        return self.policy(x)

    def fit(self, x, y):
        y = torch.FloatTensor(y)
        for i in range(self.epochs):
            pred_y = self.forward(x, training=True)
            loss = self.loss_fn(pred_y, y)
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()
        acc = pred_y.argmax(dim=1).eq(y.argmax(dim=1)).sum().numpy()/len(y)
        return loss.item(), acc

    def get_status(self, input, target):
        y = torch.FloatTensor(target)
        pred_y = self.forward(input)
        loss = self.loss_fn(pred_y, y)
        acc = pred_y.argmax(dim=1).eq(y.argmax(dim=1)).sum().numpy()/len(y)
        return loss.item(), acc

    def transform_input(self, x):
        x = torch.FloatTensor(x)
        x1 = x.t()[0].reshape(-1,1) # player data
        x2 = x.t()[1:].t().reshape(-1,self.size**2) # board data
        x2 = x2.reshape(-1, 1, self.size, self.size)
        return x1, x2

    def get_move(self, env):
        legal = env.get_legal_actions()
        factor = [1 if move in legal else 0 for move in env.all_moves]
        probs = self.forward(env.flat_state).data.numpy()[0]
        sum = 0
        new_probs = np.zeros(env.size ** 2)
        for i in range(env.size ** 2):
            if factor[i]:
                sum += probs[i]
                new_probs[i] = probs[i]
            else:
                new_probs[i] = 0
        new_probs /= sum
        indices = np.arange(env.size ** 2)
        stoch_index = np.random.choice(indices, p=new_probs)
        greedy_index = np.argmax(new_probs)
        return new_probs, stoch_index, greedy_index

    def save(self, size, level):
        torch.save(self.state_dict(), "models/{}_CNN_level_{}".format(size,level))
        print("Model has been saved to models/{}_CNN_level_{}".format(size,level))

    def load(self, size, level):
        self.load_state_dict(torch.load("models/{}_CNN_level_{}".format(size,level)))
        print("Loaded model from models/{}_CNN_level_{}".format(size,level))

    def __choose_optimizer(self, params, optimizer):
        return {
            "Adagrad": torch.optim.Adagrad(params, lr=self.alpha),
            "SGD": torch.optim.SGD(params, lr=self.alpha),
            "RMSprop": torch.optim.RMSprop(params, lr=self.alpha),
            "Adam": torch.optim.Adam(params, lr=self.alpha)
        }[optimizer]

    def __choose_activation_fn(self, activation_fn):
        return {
            "ReLU": nn.ReLU(),
            "Tanh": nn.Tanh(),
            "Sigmoid": nn.Sigmoid(),
        }[activation_fn]
