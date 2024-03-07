//
//  UserNetworkService.swift
//  DemoApp
//
//  Created by Navnit Baldha on 07/03/24.
//

import Foundation
import NBNetworking
import Combine

protocol UserNetworkService {
    func getUserData(url: String) -> AnyPublisher<[UserModel], NBURLSessionError>
}

struct UserNetworkClient: UserNetworkService {
    static let shared = UserNetworkClient()
    private let networkClient: NetworkingClient
    init(networkClient: NetworkingClient = NetworkingClient(baseUrl: APIEndPoints.baseURL)) {
        self.networkClient = networkClient
    }
}

extension UserNetworkClient {
    func getUserData(url: String) -> AnyPublisher<[UserModel], NBURLSessionError> {
         self.networkClient.get(requestUrl: url, header: nil)
    }
}
